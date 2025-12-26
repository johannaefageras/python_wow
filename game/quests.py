from typing import Dict, List

from game.data_loader import ContentIndex
from game.state import Player


def _quest_can_start(content: ContentIndex, player: Player, quest: Dict) -> bool:
    if quest["id"] in player.completed_quests or quest["id"] in player.active_quests:
        return False
    if quest.get("level_required", 1) > player.level:
        return False
    prereqs = quest.get("prerequisites", [])
    for pre in prereqs:
        if pre not in player.completed_quests:
            return False
    return True


def quests_available_at_location(content: ContentIndex, player: Player, location_id: str) -> List[Dict]:
    zone_id, loc = content.locations.get(location_id, (None, {}))
    offered: List[Dict] = []
    if not loc:
        return offered
    for npc_id in loc.get("npcs", []):
        npc = content.npcs.get(npc_id)
        if not npc:
            continue
        for qid in npc.get("quests_offered", []):
            quest = content.quests.get(qid)
            if quest and _quest_can_start(content, player, quest):
                offered.append(quest)
    return offered


def quest_status_lines(content: ContentIndex, player: Player) -> List[str]:
    lines: List[str] = []
    for qid, progress in player.active_quests.items():
        quest = content.quests.get(qid, {"name": qid, "objectives": []})
        header = f"{quest.get('name', qid)} (Lvl {quest.get('recommended_level', quest.get('level_required', 1))})"
        lines.append(header)
        for obj in quest.get("objectives", []):
            key = _objective_key(obj)
            have = progress.get(key, 0)
            need = obj.get("count", 0) if obj.get("type") in ("kill", "collect") else 1
            desc = obj.get("description", obj.get("type"))
            if obj.get("type") == "delivery":
                have = 1 if player.inventory.get(obj.get("item_id", ""), 0) >= obj.get("count", 1) else 0
                need = 1
            lines.append(f"  - {desc}: {have}/{need}")
    return lines


def accept_quest(player: Player, quest: Dict) -> None:
    # Initialize progress counts
    progress: Dict[str, int] = {}
    for obj in quest.get("objectives", []):
        key = f"{obj['type']}:{obj.get('enemy_id') or obj.get('item_id') or obj.get('target_npc') or obj.get('description')}"
        progress[key] = 0
    player.active_quests[quest["id"]] = progress


def _objective_key(obj: Dict) -> str:
    return f"{obj['type']}:{obj.get('enemy_id') or obj.get('item_id') or obj.get('target_npc') or obj.get('description')}"


def record_kill(player: Player, quest_defs: Dict[str, Dict], enemy_id: str) -> None:
    for qid, progress in player.active_quests.items():
        quest = quest_defs.get(qid)
        if not quest:
            continue
        for obj in quest.get("objectives", []):
            if obj["type"] == "kill" and obj.get("enemy_id") == enemy_id:
                key = _objective_key(obj)
                if progress.get(key, 0) < obj.get("count", 0):
                    progress[key] = progress.get(key, 0) + 1


def record_collect(player: Player, quest_defs: Dict[str, Dict], item_id: str) -> None:
    for qid, progress in player.active_quests.items():
        quest = quest_defs.get(qid)
        if not quest:
            continue
        for obj in quest.get("objectives", []):
            if obj["type"] == "collect" and obj.get("item_id") == item_id:
                key = _objective_key(obj)
                have = player.inventory.get(item_id, 0)
                needed = obj.get("count", 0)
                progress[key] = min(needed, have)


def is_quest_complete(player: Player, quest: Dict) -> bool:
    progress = player.active_quests.get(quest["id"], {})
    for obj in quest.get("objectives", []):
        key = _objective_key(obj)
        if obj["type"] in ("kill", "collect"):
            if progress.get(key, 0) < obj.get("count", 0):
                return False
        elif obj["type"] == "delivery":
            # delivery: ensure item is in inventory
            if player.inventory.get(obj.get("item_id", ""), 0) < obj.get("count", 1):
                return False
    return True


def turn_in_quest(player: Player, quest: Dict) -> Dict:
    """Returns rewards dict if turned in, raises if not eligible."""
    if quest["id"] not in player.active_quests:
        raise ValueError("Quest not active")
    if not is_quest_complete(player, quest):
        raise ValueError("Quest not complete")
    del player.active_quests[quest["id"]]
    player.completed_quests.append(quest["id"])
    return quest.get("rewards", {})
