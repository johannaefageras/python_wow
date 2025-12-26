import json
from pathlib import Path
from typing import Dict, List, Any, Tuple


class ContentIndex:
    """
    Light-weight index over the JSON content so the engine can look up IDs quickly.
    Raw structures are stored; game logic can layer richer models on top.
    """

    def __init__(self, root: Path):
        self.root = root
        self.races: List[Dict[str, Any]] = []
        self.classes: List[Dict[str, Any]] = []
        self.abilities: Dict[str, Dict[str, Any]] = {}
        self.items: Dict[str, Dict[str, Any]] = {}
        self.enemies: Dict[str, Dict[str, Any]] = {}
        self.npcs: Dict[str, Dict[str, Any]] = {}
        self.quests: Dict[str, Dict[str, Any]] = {}
        self.zones: Dict[str, Dict[str, Any]] = {}
        self.locations: Dict[str, Tuple[str, Dict[str, Any]]] = {}

    def load(self) -> "ContentIndex":
        self._load_races()
        self._load_classes()
        self._load_abilities()
        self._load_items()
        self._load_enemies()
        self._load_npcs()
        self._load_quests()
        self._load_zones()
        return self

    def _read_json(self, relative: str) -> Any:
        path = self.root / relative
        with path.open() as fh:
            return json.load(fh)

    def _load_races(self) -> None:
        data = self._read_json("races.json")
        self.races = data.get("races", [])

    def _load_classes(self) -> None:
        data = self._read_json("classes.json")
        self.classes = data.get("classes", [])

    def _load_abilities(self) -> None:
        data = self._read_json("abilities.json")
        for ability in data.get("abilities", []):
            self.abilities[ability["id"]] = ability

    def _flatten_item_dict(self, items: Dict[str, Any]) -> None:
        for category, content in items.items():
            if isinstance(content, dict):
                for sub in content.values():
                    for entry in sub:
                        self.items[entry["id"]] = entry
            elif isinstance(content, list):
                for entry in content:
                    self.items[entry["id"]] = entry

    def _load_items(self) -> None:
        data = self._read_json("items.json")
        items = data.get("items", {})
        self._flatten_item_dict(items)

    def _load_enemies(self) -> None:
        data = self._read_json("enemies.json")
        enemies_by_zone = data.get("enemies", {})
        for zone_id, enemies in enemies_by_zone.items():
            for enemy in enemies:
                enemy_copy = dict(enemy)
                enemy_copy["_zone_id"] = zone_id
                self.enemies[enemy["id"]] = enemy_copy

    def _load_npcs(self) -> None:
        data = self._read_json("npcs.json")
        npcs_by_zone = data.get("npcs", {})
        for zone_id, npcs in npcs_by_zone.items():
            for npc in npcs:
                npc_copy = dict(npc)
                npc_copy["_zone_id"] = zone_id
                self.npcs[npc["id"]] = npc_copy

    def _load_quests(self) -> None:
        data = self._read_json("quests.json")
        quests_by_zone = data.get("quests", {})
        for zone_id, quests in quests_by_zone.items():
            for quest in quests:
                quest_copy = dict(quest)
                quest_copy["_zone_id"] = zone_id
                self.quests[quest["id"]] = quest_copy

    def _load_zones(self) -> None:
        zones_dir = self.root / "zones"
        for zone_file in zones_dir.glob("*.json"):
            zone_data = self._read_json(f"zones/{zone_file.name}")
            zone = zone_data.get("zone", {})
            zone_id = zone.get("id")
            if not zone_id:
                continue
            self.zones[zone_id] = zone
            for location in zone.get("locations", []):
                loc_id = location.get("id")
                if loc_id:
                    self.locations[loc_id] = (zone_id, location)


def load_content(root: str = "data") -> ContentIndex:
    """Convenience loader."""
    return ContentIndex(Path(root)).load()
