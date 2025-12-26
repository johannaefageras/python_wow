import random
from typing import Dict, Tuple, List

from game.data_loader import ContentIndex
from game.state import Player


def _get_class(content: ContentIndex, class_id: str) -> Dict:
    return next(c for c in content.classes if c["id"] == class_id)


def _get_race(content: ContentIndex, race_id: str) -> Dict:
    return next(r for r in content.races if r["id"] == race_id)


def _collect_equipment_stats(content: ContentIndex, equipment: Dict[str, str]) -> Dict[str, int]:
    stats: Dict[str, int] = {}
    for item_id in equipment.values():
        if not item_id:
            continue
        item = content.items.get(item_id)
        if not item:
            continue
        for stat, value in item.get("stats", {}).items():
            stats[stat] = stats.get(stat, 0) + value
    return stats


def compute_base_stats(content: ContentIndex, player: Player) -> Tuple[Dict[str, int], Dict[str, float]]:
    cls = _get_class(content, player.class_id)
    race = _get_race(content, player.race_id)

    stats = dict(cls.get("base_stats", {}))
    mods: Dict[str, float] = {}

    # Race modifiers
    race_mods = race.get("stat_modifiers", {})
    for key, val in race_mods.items():
        mods[key] = val

    # Equipment stats
    equipment_stats = _collect_equipment_stats(content, player.equipment)
    for stat, val in equipment_stats.items():
        stats[stat] = stats.get(stat, 0) + val

    # Primary health/resource
    base_health = stats.get("health", 0)
    stamina = stats.get("stamina", 0)
    health_bonus = race_mods.get("max_health_bonus", 0)
    max_health = base_health + stamina * 5 + health_bonus

    res_def = cls.get("resource", {})
    max_resource = res_def.get("max", 0)
    if res_def.get("type") == "mana":
        max_resource += int(race_mods.get("max_mana_bonus", 0))

    return (
        {
          "strength": stats.get("strength", 0),
          "agility": stats.get("agility", 0),
          "intellect": stats.get("intellect", 0),
          "stamina": stats.get("stamina", 0),
          "armor": stats.get("armor", 0),
          "health": max_health,
          "resource_max": max_resource
        },
        mods
    )


def initialize_player(content: ContentIndex, name: str, race_id: str, class_id: str, zone_id: str, location_id: str) -> Player:
    cls = _get_class(content, class_id)

    # Starting equipment
    equipment: Dict[str, str] = {}
    for slot, item_id in cls.get("starting_equipment", {}).items():
        equipment[slot] = item_id

    # Starting abilities
    abilities = list(cls.get("starting_abilities", []))

    player = Player(
        name=name,
        race_id=race_id,
        class_id=class_id,
        level=1,
        experience=0,
        gold=0,
        location_id=location_id,
        zone_id=zone_id,
        equipment=equipment,
        abilities=abilities,
    )

    recalc_stats(content, player, full_restore=True)

    # Inventory seeded with equipped items counts
    for item_id in equipment.values():
        if item_id:
            player.inventory[item_id] = player.inventory.get(item_id, 0) + 1

    return player


def recalc_stats(content: ContentIndex, player: Player, full_restore: bool = False) -> None:
    """Recompute stats and derived values after gear/level changes."""
    stats, mods = compute_base_stats(content, player)
    prev_health = player.health
    prev_resource = player.resource
    player.stats = stats
    player.modifiers = mods
    player.max_health = stats["health"]
    player.max_resource = stats["resource_max"]
    if full_restore:
        player.health = player.max_health
        player.resource = player.max_resource
    else:
        player.health = min(prev_health, player.max_health)
        player.resource = min(prev_resource, player.max_resource)


def level_up(content: ContentIndex, player: Player, levels: int = 1) -> None:
    cls = _get_class(content, player.class_id)
    growth = cls.get("stat_growth_per_level", {})
    for _ in range(levels):
        player.level += 1
        for stat, inc in growth.items():
            player.stats[stat] = player.stats.get(stat, 0) + inc
        # Recompute derived
        player.max_health = player.stats.get("health", 0) + player.stats.get("stamina", 0) * 5 + int(player.modifiers.get("max_health_bonus", 0))
        player.health = player.max_health
        res_def = cls.get("resource", {})
        if res_def.get("type") == "mana":
            player.max_resource = res_def.get("max", 0) + int(player.modifiers.get("max_mana_bonus", 0))
        else:
            player.max_resource = res_def.get("max", 0)
        player.resource = player.max_resource
        # Unlock abilities
        for ability in cls.get("abilities", []):
            if ability["level"] == player.level and ability["id"] not in player.abilities:
                player.abilities.append(ability["id"])


def gain_experience(content: ContentIndex, player: Player, xp: int) -> None:
    player.experience += xp
    curve = content._read_json("config/balance.json")["balance"]["experience"]["xp_curve"]
    # Build lookup
    xp_needed = {entry["level"]: entry["xp_to_next"] for entry in curve}
    leveled = 0
    while True:
        needed = xp_needed.get(player.level)
        if not needed:
            break
        if player.experience >= needed:
            player.experience -= needed
            level_up(content, player, 1)
            leveled += 1
        else:
            break
    if leveled:
        print(f"Leveled up to {player.level}!")
