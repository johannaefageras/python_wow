import random
from typing import Dict, List, Tuple

from rich.console import Console
from rich.table import Table

from game.data_loader import ContentIndex
from game.state import Player, GameState
from game.character import gain_experience


console = Console()


def _player_attack_power(content: ContentIndex, player: Player) -> float:
    cls = next(c for c in content.classes if c["id"] == player.class_id)
    primary = cls.get("primary_stat") or "strength"
    weapon_damage = 0
    weapon_id = player.equipment.get("weapon")
    if weapon_id:
        weapon = content.items.get(weapon_id, {})
        weapon_damage = weapon.get("stats", {}).get("damage_bonus", 0)
    base = 5 + player.stats.get(primary, 0) * 0.5 + weapon_damage
    bonus = player.modifiers.get("damage_bonus", 0)
    return base * (1 + bonus)


def _apply_variance(bal: Dict, value: float) -> float:
    rng_min = bal["damage_variance"]["min"]
    rng_max = bal["damage_variance"]["max"]
    return value * random.uniform(rng_min, rng_max)


def _load_balance(content: ContentIndex) -> Dict:
    return content._read_json("config/balance.json")["balance"]


def _enemy_by_id(content: ContentIndex, enemy_id: str) -> Dict:
    return content.enemies[enemy_id]


def _roll_loot(player: Player, enemy: Dict, content: ContentIndex) -> Tuple[int, List[str]]:
    gold = random.randint(enemy.get("gold", {}).get("min", 0), enemy.get("gold", {}).get("max", 0))
    items: List[str] = []
    for entry in enemy.get("loot_table", []):
        if random.random() <= entry.get("drop_chance", 0):
            items.append(entry["item_id"])
    for item_id in items:
        player.inventory[item_id] = player.inventory.get(item_id, 0) + 1
    player.gold += gold
    return gold, items


def _render_status(player: Player, enemy: Dict, enemy_hp: int):
    console.print(f"[cyan]{player.name}[/cyan] HP {player.health}/{player.max_health} | Resource {player.resource}/{player.max_resource}")
    console.print(f"[red]{enemy['name']}[/red] HP {enemy_hp}/{enemy['health']}")


def _usable_abilities(content: ContentIndex, player: Player, enemy_hp: int, enemy_max: int) -> List[str]:
    usable = []
    for ability_id in player.abilities:
        ability = content.abilities.get(ability_id)
        if not ability:
            continue
        # Cooldown check
        if player.ability_cooldowns.get(ability_id, 0) > 0:
            continue
        # Resource check
        cost = ability.get("resource_cost", 0) or 0
        if player.resource < cost:
            continue
        cond = ability.get("conditions", {})
        if cond.get("target_health_below") and enemy_hp / enemy_max > cond["target_health_below"]:
            continue
        usable.append(ability_id)
    return usable


def _apply_ability(content: ContentIndex, player: Player, enemy: Dict, enemy_hp: int, ability_id: str) -> Tuple[int, str]:
    ability = content.abilities[ability_id]
    cost = ability.get("resource_cost", 0) or 0
    player.resource = max(0, player.resource - cost)
    player.ability_cooldowns[ability_id] = ability.get("cooldown", 0)

    dmg = ability.get("damage")
    if dmg:
        base = dmg.get("base", 0)
        stat = dmg.get("scaling_stat")
        scale = dmg.get("scaling_factor", 0)
        stat_val = player.stats.get(stat, 0)
        total = base + stat_val * scale
        if dmg.get("hits_all_enemies"):
            # Single target encounter; treat as single hit
            pass
        total = int(_apply_variance(_load_balance(content)["combat"], total))
        enemy_hp -= total
        # Rage generation on damage dealt
        cls = next(c for c in content.classes if c["id"] == player.class_id)
        res = cls.get("resource", {})
        if res.get("type") == "rage":
            player.resource = min(player.max_resource, player.resource + res.get("gain_on_damage_dealt", 0))
        return enemy_hp, f"You use {ability['name']} for {total} damage."

    return enemy_hp, f"You use {ability['name']}."


def _tick_cooldowns(player: Player):
    for ab, cd in list(player.ability_cooldowns.items()):
        if cd > 0:
            player.ability_cooldowns[ab] = cd - 1


def _armor_multiplier(bal: Dict, armor: int) -> float:
    reduction = armor * bal["armor"]["reduction_per_point"]
    mult = 1 - reduction
    return max(bal["armor"]["minimum_multiplier"], min(bal["armor"]["maximum_multiplier"], mult))


def _apply_combat_regen(content: ContentIndex, player: Player):
    bal = _load_balance(content)
    health_regen = int(player.max_health * bal["regeneration"]["health"]["in_combat_percent_per_turn"])
    if health_regen > 0:
        player.health = min(player.max_health, player.health + health_regen)
    cls = next(c for c in content.classes if c["id"] == player.class_id)
    res = cls.get("resource", {})
    rtype = res.get("type")
    if rtype == "mana":
        regen = res.get("regen_per_turn", bal["regeneration"]["mana"]["in_combat_percent_per_turn"] * player.max_resource)
        player.resource = min(player.max_resource, player.resource + int(regen))
    elif rtype == "energy":
        regen = res.get("regen_per_turn", bal["regeneration"]["energy"]["per_turn"])
        player.resource = min(player.max_resource, player.resource + int(regen))
    elif rtype == "focus":
        regen = res.get("regen_per_turn", bal["regeneration"]["focus"]["per_turn"])
        player.resource = min(player.max_resource, player.resource + int(regen))


def start_combat(content: ContentIndex, state: GameState, enemy_id: str) -> Tuple[bool, str, List[str]]:
    bal = _load_balance(content)
    player = state.player
    enemy = _enemy_by_id(content, enemy_id)
    enemy_hp = enemy["health"]
    console.print(f"[red]An enemy approaches: {enemy['name']} (Level {enemy['level']})[/red]")

    while enemy_hp > 0 and player.health > 0:
        _render_status(player, enemy, enemy_hp)
        usable = _usable_abilities(content, player, enemy_hp, enemy["health"])
        options = ["attack", "flee"] + usable
        table = Table(title="Actions")
        table.add_column("No.", justify="right")
        table.add_column("Action")
        for idx, opt in enumerate(options, start=1):
            table.add_row(str(idx), opt)
        console.print(table)
        console.print("[dim]Tip: attack for weapon damage, flee to try escaping (50%), abilities spend your resource (e.g., smite deals damage, lesser_heal restores HP).[/dim]")
        choice = console.input("Choose action (number), or type 'flee' to try escaping, 'help' to see tips: ").strip().lower()
        if choice == "help":
            console.print("[dim]Enter a number from the table. Flee is option 2 or type 'flee'. Abilities cost resource; heals restore your HP.[/dim]")
            continue
        if choice == "exit":
            console.print("You withdraw from combat.")
            return False, enemy_id, []
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            action = options[int(choice) - 1]
        else:
            action = choice

        log = ""
        if action == "attack":
            dmg = _apply_variance(bal["combat"], _player_attack_power(content, player))
            # Hit/crit
            if random.random() > bal["combat"]["base_hit_chance"]:
                log = "Your attack misses!"
            else:
                crit = random.random() < bal["combat"]["crit_chance"]
                if crit:
                    dmg *= bal["combat"]["crit_multiplier"]
                # Armor reduction
                dmg = dmg * _armor_multiplier(bal["combat"], enemy.get("armor", 0))
                dmg = int(dmg)
                enemy_hp -= dmg
                log = f"You strike for {dmg}{' (crit)' if crit else ''} damage."
                # Rage gain on damage dealt
                cls = next(c for c in content.classes if c["id"] == player.class_id)
                res = cls.get("resource", {})
                if res.get("type") == "rage":
                    player.resource = min(player.max_resource, player.resource + res.get("gain_on_damage_dealt", 0))
        elif action == "flee":
            if random.random() < 0.5:
                console.print("You fled successfully.")
                _tick_cooldowns(player)
                return True, enemy_id, []
            else:
                console.print("Failed to flee!")
        elif action in usable:
            enemy_hp, log = _apply_ability(content, player, enemy, enemy_hp, action)
        else:
            console.print("Invalid action.")
            continue

        console.print(log)
        if enemy_hp <= 0:
            break

        # Enemy turn
        edmg = random.randint(enemy["damage"]["min"], enemy["damage"]["max"])
        # Apply player armor reduction
        edmg = int(edmg * _armor_multiplier(bal["combat"], player.stats.get("armor", 0)))
        if random.random() > bal["combat"]["base_hit_chance"]:
            console.print(f"[red]{enemy['name']}'s attack misses you.[/red]")
        else:
            crit = random.random() < bal["combat"]["crit_chance"]
            if crit:
                edmg = int(edmg * bal["combat"]["crit_multiplier"])
            player.health -= edmg
            console.print(f"[red]{enemy['name']} hits you for {edmg}{' (crit)' if crit else ''} damage.[/red]")
            # Rage on damage taken
            cls = next(c for c in content.classes if c["id"] == player.class_id)
            res = cls.get("resource", {})
            if res.get("type") == "rage":
                player.resource = min(player.max_resource, player.resource + res.get("gain_on_damage_taken", 0))
        _tick_cooldowns(player)
        _apply_combat_regen(content, player)

    if player.health <= 0:
        console.print("[bold red]You have been defeated.[/bold red]")
        return False, enemy_id, []

    console.print(f"[green]You defeated {enemy['name']}![/green]")
    gold, items = _roll_loot(player, enemy, content)
    console.print(f"Looted {gold} gold" + (f" and items: {', '.join(items)}" if items else ""))
    gain_experience(content, player, enemy.get("experience", 0))
    if enemy.get("type") == "boss" or enemy_id not in state.defeated_bosses and enemy.get("boss"):
        state.defeated_bosses.append(enemy_id)
        state.world_flags[f"boss_{enemy_id}_defeated"] = True
    return True, enemy_id, items
