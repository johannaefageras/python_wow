from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Player:
    name: str
    race_id: str
    class_id: str
    level: int = 1
    experience: int = 0
    gold: int = 0
    location_id: str = ""
    zone_id: str = ""
    health: int = 0
    max_health: int = 0
    resource: int = 0
    max_resource: int = 0
    stats: Dict[str, int] = field(default_factory=dict)
    modifiers: Dict[str, float] = field(default_factory=dict)
    inventory: Dict[str, int] = field(default_factory=dict)
    equipment: Dict[str, Optional[str]] = field(default_factory=dict)
    abilities: List[str] = field(default_factory=list)
    ability_cooldowns: Dict[str, int] = field(default_factory=dict)
    active_quests: Dict[str, Dict[str, int]] = field(default_factory=dict)
    completed_quests: List[str] = field(default_factory=list)


@dataclass
class GameState:
    player: Player
    content_root: str = "data"
    vendor_stock: Dict[str, Dict[str, int]] = field(default_factory=dict)
    world_flags: Dict[str, bool] = field(default_factory=dict)
    defeated_bosses: List[str] = field(default_factory=list)

    def change_location(self, zone_id: str, location_id: str) -> None:
        self.player.zone_id = zone_id
        self.player.location_id = location_id
