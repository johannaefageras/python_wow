# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a CLI-based text adventure RPG inspired by World of Warcraft, built with Python. Players create characters (choosing race and class), explore zones, accept and complete quests, fight enemies in turn-based combat, manage inventory and equipment, and progress through leveling.

## Running the Game

```bash
# Install dependencies
pip install -r requirements.txt

# Run the game
python main.py

# Run with custom data directory
python main.py --data-root ./custom_data
```

## Development Commands

The game has no automated tests currently. All testing is manual via playing the game.

## Architecture

### Core Modules (game/)

- **data_loader.py**: `ContentIndex` class loads all JSON content from `data/` into dictionaries and lists for fast lookup. Acts as the central data registry. Methods prefixed with `_load_*` parse each content type and build lookup tables.

- **state.py**: Defines `Player` (character state: stats, location, quests, inventory, equipment) and `GameState` (player + world state: vendor stock, world flags, defeated bosses). All game state is stored in these dataclasses.

- **character.py**: Character creation, stat calculation, leveling, and XP gain. Key functions:
  - `initialize_player()`: Creates a new player with race/class starting values
  - `recalc_stats()`: Recomputes derived stats (health, armor, etc.) after equipment/level changes
  - `compute_base_stats()`: Calculates stats from class base + race modifiers + equipment
  - `level_up()`: Applies stat growth and unlocks abilities
  - `gain_experience()`: Adds XP and triggers level-ups when thresholds are reached

- **combat.py**: Turn-based combat system with `start_combat()` as entry point. Returns (won, enemy_id, items). Combat loop handles player actions (attack, abilities, flee), enemy AI, damage calculation with variance/armor/crits, resource generation (rage/mana/energy), cooldowns, and loot rolling.

- **quests.py**: Quest logic for accepting, progressing, and turning in quests. Tracks objectives (kill, collect, delivery) in `player.active_quests`. Functions:
  - `quests_available_at_location()`: Returns quests player can accept at current location
  - `accept_quest()`: Initializes quest progress tracking
  - `record_kill()` / `record_collect()`: Updates quest progress
  - `is_quest_complete()`: Checks if all objectives met
  - `turn_in_quest()`: Completes quest and returns rewards

### Main Loop (main.py)

The CLI game loop in `main()`:
1. Character creation flow (name, race, class)
2. Command parsing with aliases (e.g., 'l' → 'look', 't' → 'travel')
3. Command handlers for: look, travel, fight, stats, inventory, equip, vendor, talk, quests, accept, turnin, save/load
4. Uses Rich library for formatted tables and colored output

### Data Layer (data/)

All game content is defined in JSON files:

- **classes.json**: Class definitions with resource types (rage/mana/energy/focus), base stats, stat growth per level, proficiencies, abilities unlocked at each level, and starting equipment
- **races.json**: Race definitions with stat modifiers (e.g., health bonuses, mana bonuses) and starting zones
- **abilities.json**: Ability definitions with resource costs, cooldowns, damage formulas with stat scaling, and conditions (e.g., execute only works below 20% health)
- **items.json**: Equipment (weapons, armor, accessories) and consumables with stats, slot, proficiency requirements, buy/sell values, and loot rarity
- **enemies.json**: Organized by zone. Each enemy has level, health, damage range, armor, loot table (item_id + drop_chance), gold drops, and XP reward. Boss enemies have "boss": true flag
- **npcs.json**: Organized by zone. NPCs have dialogue lines (greeting, quest_available, quest_complete, idle), roles (quest_giver, vendor, trainer), quests_offered list, and vendor_inventory (for vendors)
- **quests.json**: Organized by zone. Quests have quest_giver (npc_id), turn_in_npc, prerequisites, level_required, objectives array (type: kill/collect/delivery with targets and counts), and rewards (experience, gold, items)
- **zones/*.json**: Zone files define the world structure. Each zone has id, name, level_range, locations array, and ambient_enemies. Locations have connections to other locations (with optional unlock_flag requirements), npcs present, enemies that can spawn, and points_of_interest

- **config/balance.json**: Game balance tuning including XP curves, combat formulas (hit chance, crit, damage variance, armor reduction), regeneration rates per resource type, loot drop weights, and vendor pricing modifiers

## Key Patterns

### Resource Systems
Classes use different resource types that generate/regenerate differently:
- **Rage** (Warrior): Starts at 0, gains on damage dealt/taken, decays out of combat
- **Mana** (Priest, Mage): Starts at max, regenerates slowly in combat, quickly out of combat
- **Energy** (Rogue): Regenerates fixed amount per turn
- **Focus** (Hunter): Similar to energy with different rates

### Quest Progression
Quests track progress in `player.active_quests[quest_id]` as a dict of `"type:target"` keys to counts. Example: `{"kill:kobold_worker": 5, "collect:kobold_candle": 3}`. After combat/looting, `record_kill()` and `record_collect()` increment these counters for all active quests.

### Location System
Locations are stored in `ContentIndex.locations` as `{location_id: (zone_id, location_dict)}`. This allows quick lookup by location_id without knowing the zone. Connections between locations define travel edges, and some require world flags (e.g., "quest_foo_complete") set by quest completion or boss defeat.

### Stat Calculation
Stats are computed as: `base_stats (class) + race_modifiers + equipment_stats`. Health = `base_health + stamina * 5 + race_health_bonus`. Armor reduces damage as a percentage (`armor * 0.01`) capped between 20%-80% multiplier.

### Save System
Save/load serializes the entire `GameState` dataclass to JSON. On load, the game reconstructs the content index from data files, then applies the saved state on top. Vendor stock persistence prevents vendor stock resets.

## Adding Content

- **New abilities**: Add to `data/abilities.json`, then reference in class ability list with unlock level
- **New items**: Add to appropriate category in `data/items.json` with stats, slot, and proficiency type
- **New enemies**: Add to zone section in `data/enemies.json` with loot table, then add to zone's `ambient_enemies` or location's `enemies` list
- **New quests**: Add to zone section in `data/quests.json`, ensure quest_giver NPC has quest_id in their `quests_offered` list
- **New locations**: Add to zone's `locations` array in `data/zones/<zone>.json`, set up connections to link to existing locations
- **New zones**: Create `data/zones/<zone_name>.json` with zone structure, update race starting zones if needed

## Code Conventions

- Use dataclasses for state objects (Player, GameState)
- ContentIndex holds raw dicts/lists; game logic modules handle business logic
- Command handlers in main.py should be concise; delegate complex logic to game modules
- Use Rich Console for all user-facing output (tables, colors, formatting)
- Function names prefixed with `_` are internal/private helpers
