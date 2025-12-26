import sys
import json
import random
from dataclasses import asdict
from typing import List, Tuple, Dict, Optional

import click
from rich.console import Console
from rich.table import Table

from game.data_loader import load_content, ContentIndex
from game.state import GameState, Player
from game.character import initialize_player, recalc_stats
from game.combat import start_combat
from game.quests import (
    quests_available_at_location,
    accept_quest,
    turn_in_quest,
    record_kill,
    record_collect,
    quest_status_lines,
    is_quest_complete,
)


console = Console()


# Global context for numbered options - allows typing just "1", "2", etc.
# Each entry is (action_type, target_id) e.g. ("talk", "marshal_dughan")
current_options: List[Tuple[str, str]] = []


def set_options(options: List[Tuple[str, str]]) -> None:
    """Set the current numbered options context."""
    global current_options
    current_options = options


def get_option(num: int) -> Optional[Tuple[str, str]]:
    """Get an option by number (1-indexed)."""
    if 1 <= num <= len(current_options):
        return current_options[num - 1]
    return None


def choose_from_list(prompt: str, options: List[Tuple[str, str]]) -> str:
    table = Table(title=prompt)
    table.add_column("No.", justify="right")
    table.add_column("ID")
    table.add_column("Name/Description")
    for idx, (opt_id, desc) in enumerate(options, start=1):
        table.add_row(str(idx), opt_id, desc)
    console.print(table)
    while True:
        value = console.input(f"[bold]{prompt}[/bold] (number): ").strip()
        if not value.isdigit():
            console.print("Enter a number from the list.")
            continue
        choice = int(value)
        if 1 <= choice <= len(options):
            return options[choice - 1][0]
        console.print("Invalid selection, try again.")


def find_start_location(content: ContentIndex, race_id: str) -> Tuple[str, str]:
    race = next((r for r in content.races if r["id"] == race_id), None)
    if not race:
        raise ValueError(f"Race {race_id} not found")
    zone_id = race.get("starting_zone")
    zone = content.zones.get(zone_id)
    if not zone:
        raise ValueError(f"Starting zone {zone_id} missing")
    for loc in zone.get("locations", []):
        if loc.get("is_starting_location"):
            return zone_id, loc["id"]
    # Fallback to first location if no starting flag
    first_loc = zone["locations"][0]
    return zone_id, first_loc["id"]


def describe_location(content: ContentIndex, state: GameState) -> None:
    """Display current location with numbered options for all interactables."""
    zone_id = state.player.zone_id
    location_id = state.player.location_id
    zone = content.zones.get(zone_id, {})
    loc = next((l for l in zone.get("locations", []) if l.get("id") == location_id), None)
    if not loc:
        console.print(f"[red]Unknown location {location_id}[/red]")
        return

    console.rule(f"[bold cyan]{loc['name']}[/bold cyan]")
    console.print(loc.get("description", ""))

    npcs = loc.get("npcs", [])
    enemies = loc.get("enemies", [])
    poi = loc.get("points_of_interest", [])
    connections = loc.get("connections", [])

    # Build numbered options
    options: List[Tuple[str, str]] = []
    option_num = 1

    # NPCs with numbers
    if npcs:
        console.print("\n[green]People here:[/green]")
        for npc_id in npcs:
            npc = content.npcs.get(npc_id, {"name": npc_id})
            name = npc.get("name", npc_id)
            title = f" ({npc.get('title')})" if npc.get("title") else ""
            roles = npc.get("role", [])
            role_str = ""
            if "vendor" in roles:
                role_str = " [yellow]• vendor[/yellow]"
            if "quest_giver" in roles:
                # Check if they have quests for us
                available = quests_available_at_location(content, state.player, location_id)
                has_quest = any(q.get("quest_giver") == npc_id for q in available)
                # Check if we can turn in to them
                can_turnin = False
                for qid in state.player.active_quests:
                    quest = content.quests.get(qid)
                    if quest and quest.get("turn_in_npc") == npc_id and is_quest_complete(state.player, quest):
                        can_turnin = True
                        break
                if can_turnin:
                    role_str += " [green]• quest ready to turn in![/green]"
                elif has_quest:
                    role_str += " [yellow]• has quest[/yellow]"
            
            console.print(f"  [bold white][{option_num}][/bold white] {name}{title}{role_str}")
            options.append(("talk", npc_id))
            option_num += 1

    # Available quests to accept (separate from NPCs for clarity)
    available_quests = quests_available_at_location(content, state.player, location_id)
    if available_quests:
        console.print("\n[yellow]Quests available:[/yellow]")
        for quest in available_quests:
            lvl = quest.get('recommended_level', quest.get('level_required', 1))
            giver = content.npcs.get(quest.get("quest_giver"), {}).get("name", quest.get("quest_giver"))
            console.print(f"  [bold white][{option_num}][/bold white] {quest['name']} (Lvl {lvl}) from {giver}")
            options.append(("accept", quest["id"]))
            option_num += 1

    # Quests ready to turn in here
    ready_quests = []
    for qid in state.player.active_quests:
        quest = content.quests.get(qid)
        if quest and quest.get("turn_in_npc") in npcs and is_quest_complete(state.player, quest):
            ready_quests.append(quest)
    if ready_quests:
        console.print("\n[green]Quests ready to turn in:[/green]")
        for quest in ready_quests:
            turnin_npc = content.npcs.get(quest.get("turn_in_npc"), {}).get("name", quest.get("turn_in_npc"))
            console.print(f"  [bold white][{option_num}][/bold white] {quest['name']} → {turnin_npc}")
            options.append(("turnin", quest["id"]))
            option_num += 1

    # Enemies / Fight option
    if enemies:
        enemy_names = []
        for eid in enemies[:3]:  # Show up to 3 enemy types
            enemy = content.enemies.get(eid, {})
            enemy_names.append(enemy.get("name", eid))
        more = f" and {len(enemies) - 3} more types" if len(enemies) > 3 else ""
        console.print(f"\n[red]Enemies here:[/red] {', '.join(enemy_names)}{more}")
        console.print(f"  [bold white][{option_num}][/bold white] Fight!")
        options.append(("fight", ""))
        option_num += 1

    # Travel connections
    if connections:
        console.print("\n[blue]Exits:[/blue]")
        for conn in connections:
            dest_id = conn.get("location_id") or conn.get("zone_id")
            direction = conn.get("direction", "")
            desc = conn.get("description", "")
            
            # Get destination name
            if conn.get("location_id"):
                dest_loc = next((l for l in zone.get("locations", []) if l.get("id") == conn["location_id"]), None)
                dest_name = dest_loc.get("name", dest_id) if dest_loc else dest_id
            else:
                dest_zone = content.zones.get(conn.get("zone_id"), {})
                dest_name = dest_zone.get("name", dest_id)
            
            # Check if locked
            unlock_flag = conn.get("unlock_flag")
            is_locked = unlock_flag and not state.world_flags.get(unlock_flag, False)
            lock_str = f" [red](locked: {unlock_flag})[/red]" if is_locked else ""
            
            dir_str = f"[dim]{direction}[/dim] → " if direction else ""
            console.print(f"  [bold white][{option_num}][/bold white] {dir_str}{dest_name}{lock_str}")
            options.append(("travel", f"{conn.get('zone_id') or zone_id}:{conn.get('location_id') or conn.get('location')}"))
            option_num += 1

    # Points of interest (no action, just flavor)
    if poi:
        console.print("\n[yellow]Points of Interest:[/yellow]")
        for p in poi:
            console.print(f"  • {p.get('name')}: [dim]{p.get('description')}[/dim]")

    # Set the global options context
    set_options(options)

    # Show hint about numbers
    if options:
        console.print(f"\n[dim]Enter a number (1-{len(options)}) or type a command. 'help' for all commands.[/dim]")


def npc_location(content: ContentIndex, npc_id: str) -> Optional[str]:
    npc = content.npcs.get(npc_id)
    if not npc:
        return None
    return npc.get("location")


def show_inventory(state: GameState, content: ContentIndex) -> None:
    """Show inventory with numbered equip options."""
    p = state.player
    if not p.inventory:
        console.print("Inventory empty.")
        set_options([])
        return
    
    options: List[Tuple[str, str]] = []
    option_num = 1
    
    table = Table(title="Inventory")
    table.add_column("No.", justify="right")
    table.add_column("Name")
    table.add_column("Count")
    table.add_column("Type")
    
    for item_id, count in p.inventory.items():
        item = content.items.get(item_id, {"name": item_id})
        item_type = item.get("slot", item.get("type", "misc"))
        table.add_row(str(option_num), item.get("name", item_id), str(count), item_type)
        # Only add equip option if it has a slot
        if item.get("slot"):
            options.append(("equip", item_id))
        else:
            options.append(("use", item_id))  # For consumables later
        option_num += 1
    
    console.print(table)
    set_options(options)
    
    if options:
        console.print(f"[dim]Enter a number (1-{len(options)}) to equip/use, or 'look' to return.[/dim]")


def _get_class(content: ContentIndex, class_id: str) -> Dict:
    return next(c for c in content.classes if c["id"] == class_id)


def equip_item(state: GameState, content: ContentIndex, item_id: str) -> None:
    p = state.player
    item = content.items.get(item_id)
    if not item:
        console.print("Item not found.")
        return
    if p.inventory.get(item_id, 0) <= 0:
        console.print("You do not have that item.")
        return
    slot = item.get("slot")
    if not slot:
        console.print("Item cannot be equipped.")
        return
    cls = _get_class(content, p.class_id)
    if slot == "weapon":
        if item.get("type") not in cls.get("weapon_proficiency", []):
            console.print("You are not proficient with this weapon.")
            return
    else:
        if item.get("type") not in cls.get("armor_proficiency", []):
            console.print("You are not proficient with this armor.")
            return
    # swap
    currently = p.equipment.get(slot)
    p.equipment[slot] = item_id
    p.inventory[item_id] -= 1
    if p.inventory[item_id] <= 0:
        del p.inventory[item_id]
    if currently:
        p.inventory[currently] = p.inventory.get(currently, 0) + 1
    recalc_stats(content, p, full_restore=False)
    console.print(f"Equipped {item.get('name', item_id)} to {slot}.")


def _balance(content: ContentIndex) -> Dict:
    return content._read_json("config/balance.json")["balance"]


def vendor_interaction(state: GameState, content: ContentIndex, npc_id: str) -> None:
    p = state.player
    loc_zone, loc = content.locations.get(p.location_id, (None, {}))
    if npc_id not in loc.get("npcs", []):
        console.print("That NPC is not here.")
        return
    npc = content.npcs.get(npc_id)
    if not npc or "vendor" not in npc.get("role", []):
        console.print("That NPC is not a vendor.")
        return
    bal = _balance(content)["loot"]["vendor"]
    buy_mod = bal["buy_modifier"]
    sell_mod = bal["sell_modifier"]

    # Persist vendor stock in state metadata
    vendor_state = state.vendor_stock.setdefault(npc_id, {})

    while True:
        console.print(f"\nGold: {p.gold}")
        table = Table(title=f"Shop - {npc.get('name', npc_id)}")
        table.add_column("No.", justify="right")
        table.add_column("Name")
        table.add_column("Price")
        table.add_column("Stock")
        vendor_items = []
        for stock in npc.get("vendor_inventory", []):
            item = content.items.get(stock["item_id"], {"name": stock["item_id"]})
            if "buy_value" not in item:
                continue
            price = int(item["buy_value"] * buy_mod)
            current_stock = vendor_state.get(stock["item_id"], stock.get("stock", 0))
            vendor_items.append((stock, item, price, current_stock))
        for idx, (stock, item, price, current_stock) in enumerate(vendor_items, start=1):
            table.add_row(str(idx), item.get("name", stock["item_id"]), str(price), str(current_stock))
        console.print(table)
        
        # Show player's sellable items
        if p.inventory:
            console.print("\n[yellow]Your items (sell value):[/yellow]")
            sell_options = []
            for item_id, count in p.inventory.items():
                item = content.items.get(item_id, {})
                sell_price = int(item.get("sell_value", 0) * sell_mod)
                if sell_price > 0:
                    sell_options.append((item_id, item.get("name", item_id), sell_price, count))
            for idx, (iid, name, price, count) in enumerate(sell_options, start=len(vendor_items) + 1):
                console.print(f"  [{idx}] {name} x{count} → {price}g each")
        
        console.print("\n[dim]Enter number to buy, 's <number>' to sell, or 'exit' to leave.[/dim]")
        cmd = console.input("> ").strip().lower()
        if cmd in ("exit", "leave", "q", ""):
            break
        
        parts = cmd.split()
        
        # Direct number = buy
        if cmd.isdigit():
            choice = int(cmd)
            if not (1 <= choice <= len(vendor_items)):
                console.print("Invalid choice.")
                continue
            stock, item, price, current_stock = vendor_items[choice - 1]
            if current_stock <= 0:
                console.print("Out of stock.")
                continue
            if p.gold < price:
                console.print("Not enough gold.")
                continue
            p.gold -= price
            current_stock -= 1
            vendor_state[stock["item_id"]] = current_stock
            p.inventory[item["id"]] = p.inventory.get(item["id"], 0) + 1
            console.print(f"Bought {item.get('name', item['id'])}.")
            record_collect(p, content.quests, item["id"])
        # s <number> = sell
        elif parts[0] == "s" and len(parts) == 2 and parts[1].isdigit():
            sell_idx = int(parts[1]) - len(vendor_items) - 1
            sell_options = []
            for item_id, count in p.inventory.items():
                item = content.items.get(item_id, {})
                sell_price = int(item.get("sell_value", 0) * sell_mod)
                if sell_price > 0:
                    sell_options.append((item_id, item.get("name", item_id), sell_price))
            if not (0 <= sell_idx < len(sell_options)):
                console.print("Invalid sell choice.")
                continue
            iid, name, price = sell_options[sell_idx]
            p.inventory[iid] -= 1
            if p.inventory[iid] <= 0:
                del p.inventory[iid]
            p.gold += price
            console.print(f"Sold {name} for {price} gold.")
        # Legacy: buy <num>
        elif parts[0] == "buy" and len(parts) == 2 and parts[1].isdigit():
            choice = int(parts[1])
            if not (1 <= choice <= len(vendor_items)):
                console.print("Invalid choice.")
                continue
            stock, item, price, current_stock = vendor_items[choice - 1]
            if current_stock <= 0:
                console.print("Out of stock.")
                continue
            if p.gold < price:
                console.print("Not enough gold.")
                continue
            p.gold -= price
            current_stock -= 1
            vendor_state[stock["item_id"]] = current_stock
            p.inventory[item["id"]] = p.inventory.get(item["id"], 0) + 1
            console.print(f"Bought {item.get('name', item['id'])}.")
            record_collect(p, content.quests, item["id"])
        # Legacy: sell <item_id>
        elif parts[0] == "sell" and len(parts) == 2:
            iid = parts[1]
            if p.inventory.get(iid, 0) <= 0:
                console.print("You don't have that item.")
                continue
            item = content.items.get(iid, {})
            price = int(item.get("sell_value", 0) * sell_mod)
            p.inventory[iid] -= 1
            if p.inventory[iid] <= 0:
                del p.inventory[iid]
            p.gold += price
            console.print(f"Sold {item.get('name', iid)} for {price} gold.")
        else:
            console.print("Invalid command. Enter a number to buy, 's <num>' to sell, or 'exit'.")


def talk_to_npc(state: GameState, content: ContentIndex, npc_id: str) -> None:
    p = state.player
    loc_zone, loc = content.locations.get(p.location_id, (None, {}))
    if npc_id not in loc.get("npcs", []):
        console.print("That NPC is not here.")
        return
    npc = content.npcs.get(npc_id, {"name": npc_id, "dialogue": {}})
    dlg = npc.get("dialogue", {})
    def line(key: str, default: str = "..."):
        val = dlg.get(key, default)
        if isinstance(val, list):
            return random.choice(val)
        return val

    console.print(f"\n[bold]{npc.get('name', npc_id)}[/bold]: \"{line('greeting')}\"")
    
    # Build options for this NPC
    options: List[Tuple[str, str]] = []
    option_num = 1
    
    # Check for available quests from this NPC
    available = quests_available_at_location(content, p, p.location_id)
    npc_quests = [q for q in available if q.get("quest_giver") == npc_id]
    if npc_quests:
        console.print(f'[yellow]"{line("quest_available", "I have work for you, if you are interested.")}"[/yellow]')
        for quest in npc_quests:
            lvl = quest.get('recommended_level', quest.get('level_required', 1))
            console.print(f"  [bold white][{option_num}][/bold white] Accept: {quest['name']} (Lvl {lvl})")
            options.append(("accept", quest["id"]))
            option_num += 1
    
    # Check for turn-ins to this NPC
    ready = []
    for qid in list(p.active_quests.keys()):
        quest = content.quests.get(qid)
        if quest and quest.get("turn_in_npc") == npc_id and is_quest_complete(p, quest):
            ready.append(quest)
    if ready:
        console.print(f'[green]"{line("quest_complete", "Ah, you have done it! Let me see...")}"[/green]')
        for quest in ready:
            console.print(f"  [bold white][{option_num}][/bold white] Turn in: {quest['name']}")
            options.append(("turnin", quest["id"]))
            option_num += 1
    
    # Vendor option
    if "vendor" in npc.get("role", []):
        console.print(f"  [bold white][{option_num}][/bold white] [yellow]Browse wares[/yellow]")
        options.append(("vendor", npc_id))
        option_num += 1
    
    if not npc_quests and not ready and "vendor" not in npc.get("role", []):
        console.print(f"[dim]\"{line('idle', 'Safe travels.')}\"[/dim]")
    
    set_options(options)
    
    if options:
        console.print(f"\n[dim]Enter a number (1-{len(options)}) or press Enter to leave.[/dim]")


def show_quests(state: GameState, content: ContentIndex) -> None:
    p = state.player
    
    if not p.active_quests and not p.completed_quests:
        console.print("No quests yet. Talk to NPCs to find work!")
        return
    
    if p.active_quests:
        console.print("\n[bold yellow]Active Quests:[/bold yellow]")
        for qid in p.active_quests:
            quest = content.quests.get(qid, {"name": qid, "objectives": []})
            console.print(f"\n  [bold]{quest.get('name', qid)}[/bold]")
            if quest.get("description"):
                console.print(f"  [dim]{quest['description']}[/dim]")
            for obj in quest.get("objectives", []):
                key = f"{obj['type']}:{obj.get('enemy_id') or obj.get('item_id') or obj.get('target_npc') or obj.get('description')}"
                progress = p.active_quests[qid].get(key, 0)
                need = obj.get("count", 0) if obj.get("type") in ("kill", "collect") else 1
                desc = obj.get("description", obj.get("type"))
                if obj.get("type") == "delivery":
                    have = 1 if p.inventory.get(obj.get("item_id", ""), 0) >= obj.get("count", 1) else 0
                    progress = have
                    need = 1
                done = "✓" if progress >= need else " "
                console.print(f"    [{done}] {desc}: {progress}/{need}")
            
            # Show turn-in location
            turnin_npc = quest.get("turn_in_npc")
            if turnin_npc:
                npc = content.npcs.get(turnin_npc, {})
                console.print(f"    [dim]Turn in to: {npc.get('name', turnin_npc)}[/dim]")

    if p.completed_quests:
        console.print(f"\n[bold green]Completed:[/bold green] {', '.join(p.completed_quests)}")


def save_game(state: GameState, path: str = "save.json") -> None:
    data = asdict(state)
    with open(path, "w") as fh:
        json.dump(data, fh, indent=2)
    console.print(f"Game saved to {path}.")


def load_game(content: ContentIndex, path: str = "save.json") -> GameState:
    with open(path) as fh:
        data = json.load(fh)
    p_data = data["player"]
    player = Player(**p_data)
    vendor_stock = data.get("vendor_stock", {})
    world_flags = data.get("world_flags", {})
    defeated_bosses = data.get("defeated_bosses", [])
    return GameState(
        player=player,
        content_root=data.get("content_root", "data"),
        vendor_stock=vendor_stock,
        world_flags=world_flags,
        defeated_bosses=defeated_bosses,
    )


def do_travel(state: GameState, content: ContentIndex, dest_str: str) -> bool:
    """Execute travel to a destination. dest_str is 'zone_id:location_id'."""
    parts = dest_str.split(":", 1)
    if len(parts) != 2:
        console.print("Invalid destination.")
        return False
    dest_zone, dest_loc = parts
    
    # Check if this is a valid connection from current location
    zone = content.zones.get(state.player.zone_id, {})
    loc = next((l for l in zone.get("locations", []) if l.get("id") == state.player.location_id), None)
    if not loc:
        return False
    
    valid = False
    for conn in loc.get("connections", []):
        conn_zone = conn.get("zone_id") or state.player.zone_id
        conn_loc = conn.get("location_id") or conn.get("location")
        if conn_zone == dest_zone and conn_loc == dest_loc:
            # Check lock
            unlock_flag = conn.get("unlock_flag")
            if unlock_flag and not state.world_flags.get(unlock_flag, False):
                console.print(f"[red]Path is locked. Requires: {unlock_flag}[/red]")
                return False
            valid = True
            break
    
    if not valid:
        console.print("You can't go there from here.")
        return False
    
    state.change_location(dest_zone, dest_loc)
    
    # Get destination name for nice message
    dest_zone_data = content.zones.get(dest_zone, {})
    dest_loc_data = next((l for l in dest_zone_data.get("locations", []) if l.get("id") == dest_loc), None)
    dest_name = dest_loc_data.get("name", dest_loc) if dest_loc_data else dest_loc
    
    console.print(f"\n[bold]Traveling to {dest_name}...[/bold]\n")
    return True


def do_fight(state: GameState, content: ContentIndex) -> None:
    """Start a fight at current location."""
    zone = content.zones.get(state.player.zone_id, {})
    loc_entry = next((l for l in zone.get("locations", []) if l.get("id") == state.player.location_id), None)
    
    enemies = []
    if loc_entry:
        enemies = list(loc_entry.get("enemies", []))
    if not enemies:
        enemies = list(zone.get("ambient_enemies", []))
    if not enemies:
        console.print("No enemies to fight here.")
        return
    
    enemy_id = random.choice(enemies)
    won, killed_id, items = start_combat(content, state, enemy_id)
    if won:
        record_kill(state.player, content.quests, killed_id)
        for iid in items:
            record_collect(state.player, content.quests, iid)


def do_accept_quest(state: GameState, content: ContentIndex, quest_id: str) -> None:
    """Accept a quest."""
    quest = content.quests.get(quest_id)
    if not quest:
        console.print("Quest not found.")
        return
    
    offered = quests_available_at_location(content, state.player, state.player.location_id)
    if quest not in offered:
        console.print("Quest not available here.")
        return
    
    accept_quest(state.player, quest)
    for obj in quest.get("objectives", []):
        if obj.get("type") == "collect":
            record_collect(state.player, content.quests, obj.get("item_id"))
    
    console.print(f"\n[green]Quest accepted: {quest['name']}[/green]")
    if quest.get("description"):
        console.print(f"[dim]{quest['description']}[/dim]")


def do_turnin_quest(state: GameState, content: ContentIndex, quest_id: str) -> None:
    """Turn in a completed quest."""
    quest = content.quests.get(quest_id)
    if not quest:
        console.print("Quest not found.")
        return
    
    loc_zone, loc = content.locations.get(state.player.location_id, (None, {}))
    npc_here = loc.get("npcs", [])
    if quest.get("turn_in_npc") not in npc_here:
        console.print("Required NPC not here.")
        return
    
    try:
        rewards = turn_in_quest(state.player, quest)
    except ValueError as e:
        console.print(str(e))
        return
    
    state.player.gold += rewards.get("gold", 0)
    for itm in rewards.get("items", []):
        state.player.inventory[itm["item_id"]] = state.player.inventory.get(itm["item_id"], 0) + itm.get("count", 1)
        record_collect(state.player, content.quests, itm["item_id"])
    
    console.print(f"\n[green]Quest complete: {quest['name']}![/green]")
    console.print(f"Rewards: {rewards.get('experience', 0)} XP, {rewards.get('gold', 0)} gold")
    
    if rewards.get("experience", 0):
        from game.character import gain_experience
        gain_experience(content, state.player, rewards["experience"])


def handle_numbered_option(state: GameState, content: ContentIndex, num: int) -> bool:
    """Handle a numbered option from the current context. Returns True if handled."""
    option = get_option(num)
    if not option:
        return False
    
    action, target = option
    
    if action == "talk":
        talk_to_npc(state, content, target)
        return True
    elif action == "accept":
        do_accept_quest(state, content, target)
        return True
    elif action == "turnin":
        do_turnin_quest(state, content, target)
        return True
    elif action == "vendor":
        vendor_interaction(state, content, target)
        return True
    elif action == "fight":
        do_fight(state, content)
        return True
    elif action == "travel":
        if do_travel(state, content, target):
            describe_location(content, state)
        return True
    elif action == "equip":
        equip_item(state, content, target)
        return True
    elif action == "use":
        console.print(f"Using {target}... (not implemented yet)")
        return True
    
    return False


@click.command()
@click.option("--data-root", default="data", help="Path to data directory.")
def main(data_root: str):
    content = load_content(data_root)

    # Character creation
    console.print("[bold cyan]═══ World of Warcraft: Text Adventure ═══[/bold cyan]\n")
    name = console.input("Enter your character's name: ").strip() or "Adventurer"
    race_id = choose_from_list(
        "Choose a race",
        [(r["id"], r["description"]) for r in content.races],
    )
    class_id = choose_from_list(
        "Choose a class",
        [(c["id"], c["description"]) for c in content.classes],
    )
    zone_id, loc_id = find_start_location(content, race_id)
    player = initialize_player(content, name=name, race_id=race_id, class_id=class_id, zone_id=zone_id, location_id=loc_id)
    state = GameState(player=player, content_root=data_root)

    console.print(f"\n[bold green]Welcome, {name} the {race_id.title()} {class_id.title()}![/bold green]")
    console.print("[dim]Your journey begins...[/dim]\n")
    
    describe_location(content, state)

    def show_help():
        console.print("\n[bold]Commands:[/bold]")
        console.print("  [white]Numbers[/white]    - Select from the numbered options shown")
        console.print("  [white]look / l[/white]   - Look around (refresh location view)")
        console.print("  [white]fight / f[/white]  - Fight enemies here")
        console.print("  [white]stats / s[/white]  - View your character stats")
        console.print("  [white]inv / i[/white]    - View inventory (with equip options)")
        console.print("  [white]quests[/white]     - View quest log")
        console.print("  [white]save[/white]       - Save your game")
        console.print("  [white]load[/white]       - Load a saved game")
        console.print("  [white]help / h[/white]   - Show this help")
        console.print("  [white]quit / q[/white]   - Exit the game")
        console.print("\n[dim]Tip: Just type numbers to interact! Talk to NPCs, accept quests, and travel.[/dim]")

    def show_stats():
        p = state.player
        console.print(f"\n[bold cyan]═══ {p.name} ═══[/bold cyan]")
        console.print(f"Level {p.level} {p.race_id.title()} {p.class_id.title()}")
        console.print(f"\n[red]HP:[/red] {p.health}/{p.max_health}")
        
        # Get resource name from class
        cls = _get_class(content, p.class_id)
        res_type = cls.get("resource", {}).get("type", "resource").title()
        console.print(f"[blue]{res_type}:[/blue] {p.resource}/{p.max_resource}")
        
        console.print(f"[yellow]Gold:[/yellow] {p.gold}  |  [green]XP:[/green] {p.experience}")
        console.print(f"\n[bold]Stats:[/bold] STR {p.stats.get('strength',0)} | AGI {p.stats.get('agility',0)} | INT {p.stats.get('intellect',0)} | STA {p.stats.get('stamina',0)} | ARM {p.stats.get('armor',0)}")
        
        if p.abilities:
            console.print(f"\n[bold]Abilities:[/bold] {', '.join(p.abilities)}")
        
        if p.equipment:
            console.print(f"\n[bold]Equipment:[/bold]")
            for slot, item_id in p.equipment.items():
                if item_id:
                    item = content.items.get(item_id, {})
                    console.print(f"  {slot}: {item.get('name', item_id)}")

    # Command aliases
    aliases = {
        "l": "look",
        "look": "look",
        "f": "fight",
        "fight": "fight",
        "s": "stats",
        "stats": "stats",
        "i": "inv",
        "inv": "inv",
        "inventory": "inv",
        "h": "help",
        "help": "help",
        "q": "quit",
        "quit": "quit",
        "exit": "quit",
        "quests": "quests",
        "quest": "quests",
        "save": "save",
        "load": "load",
    }

    # Main game loop
    while True:
        try:
            command = console.input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\nGoodbye!")
            break
        
        if not command:
            # Empty input = look around
            describe_location(content, state)
            continue
        
        # Check if it's a number
        if command.isdigit():
            num = int(command)
            if handle_numbered_option(state, content, num):
                continue
            else:
                console.print(f"[red]Invalid option: {num}[/red]")
                continue
        
        # Parse command
        parts = command.lower().split()
        base = aliases.get(parts[0], parts[0])
        args = parts[1:]
        
        if base == "quit":
            console.print("Thanks for playing!")
            break
        elif base == "help":
            show_help()
        elif base == "look":
            describe_location(content, state)
        elif base == "fight":
            do_fight(state, content)
        elif base == "stats":
            show_stats()
        elif base == "inv":
            show_inventory(state, content)
        elif base == "quests":
            show_quests(state, content)
        elif base == "save":
            save_game(state)
        elif base == "load":
            try:
                state = load_game(content)
                console.print("Game loaded!")
                describe_location(content, state)
            except FileNotFoundError:
                console.print("No save file found.")
        # Legacy commands that still work with IDs
        elif base == "talk" and args:
            talk_to_npc(state, content, args[0])
        elif base == "vendor" and args:
            vendor_interaction(state, content, args[0])
        elif base == "accept" and args:
            do_accept_quest(state, content, args[0])
        elif base == "turnin" and args:
            do_turnin_quest(state, content, args[0])
        elif base == "equip" and args:
            equip_item(state, content, args[0])
        elif base == "travel":
            # Show travel options with numbers
            describe_location(content, state)
            console.print("[dim]Use the numbered exits above to travel.[/dim]")
        else:
            console.print(f"[red]Unknown command: {command}[/red]")
            console.print("[dim]Type 'help' for commands or use numbers to interact.[/dim]")


if __name__ == "__main__":
    main()
