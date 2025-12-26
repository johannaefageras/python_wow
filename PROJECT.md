# CLI Text Adventure: World of Warcraft (Outline of Structure Approach)

## CORE CONCEPT

A text-based RPG where the player creates a character, explores zones, completes quests, fights enemies, and levels up — all through a command-line interface. The game should capture the feel of WoW's progression systems, class fantasy, and exploration while working within the constraints of a text medium.

## CHARACTER SYSTEM:

The player begins by creating a character, choosing from classic WoW-inspired races and classes. Each race could offer minor flavor differences or small stat bonuses, while classes define the core gameplay experience. A warrior might have high health and access to abilities like "Shield Block" and "Mortal Strike," while a mage would rely on mana for spells like "Fireball" and "Frost Nova." The character sheet tracks health, mana or energy (depending on class), experience points, level, equipped gear, inventory, and gold.
Progression follows the familiar loop: killing enemies and completing quests grants experience, and reaching thresholds triggers level-ups that improve stats and unlock new abilities. A simple talent or specialization system could let players customize their character further — perhaps choosing between two or three paths per class.

## COMBAT SYSTEM:

Combat could be turn-based to keep things manageable in a text interface. Each round, the player sees their current health/resources and the enemy's status, then chooses an action: attack with a basic strike, use a class ability, consume a potion, or attempt to flee. Abilities might cost mana or have cooldowns tracked in turns.
Enemy encounters can be random (while exploring) or scripted (boss fights, quest objectives). Each enemy type has its own stats and maybe a special attack pattern — a wolf might occasionally "lunge" for extra damage, while a murloc could call for reinforcements.
The combat log prints out what happens each round in a narrative style: "You cast Fireball for 45 damage. The Defias Bandit retaliates with a dagger slash for 12 damage."

## WORLD STRUCTURE:

The world is organized into zones, each with a level range, theme, and set of locations. Elwynn Forest serves new players with wolves, kobolds, and simple fetch quests. Westfall introduces tougher Defias enemies and a longer quest chain. Duskwood brings undead, worgen, and a darker atmosphere.
Within each zone, the player can move between named locations — Goldshire, the Fargodeep Mine, Sentinel Hill. Each location might have NPCs to talk to, enemies to fight, vendors to trade with, or quest objectives to complete. Navigation happens through simple commands: "go north," "travel to Goldshire," or a menu-based system showing available destinations.

## QUEST SYSTEM:

Quests drive the narrative forward and give purpose to exploration and combat. An NPC might ask you to kill ten kobolds in the mine, collect six wolf pelts, or deliver a letter to someone in the next town. Each quest tracks its objectives, and completing it rewards experience, gold, and sometimes gear.
Quest chains tell longer stories — investigating the Defias Brotherhood across multiple steps, uncovering the source of Duskwood's curse, or helping a farmer defend against gnoll raids. Some quests could have simple choices that affect dialogue or minor rewards, though branching narratives add complexity.
The quest log shows active quests, their descriptions, and current progress. Completed quests move to a history or simply disappear.

## ITEMS AND ECONOMY:

Gear improves your character's effectiveness. Weapons increase damage, armor reduces incoming damage, and accessories might boost specific stats or abilities. Each equipment slot (weapon, chest, legs, etc.) can hold one item, and the player compares stats when deciding whether to equip new loot.
Enemies drop loot — sometimes gold, sometimes items, sometimes crafting materials if you want that layer. Vendors in towns buy and sell, with better gear available in higher-level zones or as quest rewards. Inventory management requires some limit, whether a slot count or a carry weight, to create meaningful decisions about what to keep.
Consumables like health potions, food for out-of-combat regeneration, and buff items add tactical options without overcomplicating things.

## TECHNICAL ARCHITECTURE:

The codebase could be organized into several modules. A game loop module handles the main cycle of displaying information, accepting input, and updating state. A character module defines the player class with stats, inventory, abilities, and methods for taking damage, gaining experience, and equipping items. An enemy module provides enemy templates and spawning logic. A combat module orchestrates fights. A world module defines zones, locations, and navigation. A quest module tracks objectives and rewards. A data module or folder holds JSON or YAML files defining all the specific content — enemy stats, item properties, quest text, zone layouts.
Saving and loading the game means serializing the player's state and world progress to a file, probably JSON for simplicity. The player can save at any time or at designated rest points, depending on how you want to handle difficulty.

## USER INTERFACE:

The CLI interface should be clear and readable. A status bar or header might always show current health, mana, location, and level. Commands can be typed directly ("attack," "inventory," "quest log") or selected from numbered menus — the menu approach is often friendlier for this kind of game.
Color can help if you use a library like colorama or rich — green for health, blue for mana, red for enemy attacks, yellow for quest updates. ASCII art for locations, enemies, or the title screen adds atmosphere without requiring graphics.

## SCOPE AND PRIORITIES:

For a first playable version, I'd focus on: character creation with two or three classes, one starting zone with a handful of locations and enemies, basic turn-based combat with a few abilities per class, three to five quests forming a short story arc, simple inventory and equipment, and saving/loading.
From there, expansion is straightforward — add more zones, more classes, deeper quest lines, crafting, party members, dungeons with boss mechanics, PvP duels, a reputation system. The modular structure makes it easy to grow the game over time.

---

# Data Structures for WoW-Inspired Text Adventure

## CHARACTER AND PLAYER DATA

The player character is the central data structure, tracking everything about the current game state from the player's perspective.
The player structure holds identity information (name, race, class), current and maximum values for health and resource (mana, energy, or rage depending on class), experience and level, a reference to the current location, and the character's equipment, inventory, gold, known abilities, active and completed quests, and any active cooldowns or status effects.
Equipment is organized by slot — head, chest, legs, feet, hands, weapon, shield, accessory — with each slot either empty or containing a reference to an item. Inventory is a list of items with some maximum capacity. Abilities are references to the character's class abilities, potentially with unlocked/locked status based on level.
A level-up threshold table defines how much experience is needed to reach each level. When experience exceeds the threshold, the character levels up, gains stat increases (determined by class), and potentially unlocks new abilities.

## CLASS DEFINITIONS

Each class defines the template for how a character of that type functions. This includes the base stats at level one (health, resource type and amount, base damage), the stat growth per level, and the list of abilities available to the class with the level at which each unlocks.
For example, a Warrior might start with 120 health, use rage as a resource (starting at 0, generated by dealing and taking damage), have high base damage, and gain mostly health and strength per level. Their abilities might include Heroic Strike at level 1, Shield Block at level 2, Execute at level 5, and Mortal Strike at level 8.
A Mage would start with 60 health and 100 mana, have lower base damage but powerful spells, gain mostly intellect and mana per level, and have Fireball at level 1, Frost Nova at level 3, Arcane Missiles at level 5, and Pyroblast at level 10.
A Rogue might use energy that regenerates each turn, have medium health but high burst damage potential, and access abilities like Sinister Strike, Backstab, Evasion, and Cheap Shot.

## ABILITIES

Each ability is defined by its name, a description for the player, the resource cost (if any), the cooldown in combat turns (if any), the damage or healing amount (possibly expressed as a formula involving character stats), and any special effects.
Special effects might include damage-over-time (like a bleed), stuns that skip the enemy's next turn, defensive buffs that reduce incoming damage, debuffs applied to the enemy, or resource generation (like a Warrior ability that grants rage).
Some abilities might have conditions — Execute only works on low-health targets, Backstab requires the enemy to be stunned, a healing spell can't be used in combat. These conditions are part of the ability definition.

## RACES

Race definitions are simpler, primarily providing flavor and perhaps minor stat adjustments. A Human might have slightly faster experience gain, a Dwarf might have bonus health, a Night Elf could have a small chance to dodge attacks, and an Orc might deal slightly more damage. These bonuses should be small enough that race choice feels like personal preference rather than optimization.
Each race also has a text description and possibly a home starting zone, though for simplicity you might have all characters start in the same place.

## ITEMS

The item structure covers equipment, consumables, and miscellaneous items like quest objects.
Equipment items have a name, description, item type (weapon, armor piece, accessory), the slot they occupy, stat bonuses they provide (bonus damage, armor value, health increase, etc.), a level requirement, a rarity tier (common, uncommon, rare, epic), and a sell value in gold.
Consumables have a name, description, effect (restore health, restore mana, buff stats temporarily), magnitude of the effect, duration if it's a buff, stack limit in inventory, and buy/sell prices.
Quest items typically can't be sold or discarded, exist only while the relevant quest is active, and have no stats — they're just flags that the player has collected something.

## ENEMIES

Each enemy type is defined by a name, description, level, health, damage range, any special abilities or attack patterns, loot table, and experience reward.
The loot table is a list of possible drops, each with an item reference and a drop chance. A Defias Bandit might have a 50% chance to drop a small amount of gold, a 20% chance to drop a Linen Cloth, and a 5% chance to drop a green-quality dagger.
Special abilities make enemies more interesting. A wolf might have a Lunge attack that deals extra damage but only triggers occasionally. A murloc might summon reinforcements at low health. A mine kobold might flee when badly hurt. Boss enemies have more complex patterns — a sequence of abilities they cycle through, or phase transitions at health thresholds.

## LOCATIONS

A location represents a specific place the player can be. Each location has a name, a longer description displayed when the player arrives or looks around, the zone it belongs to, a list of connections to other locations (with optional direction labels like "north" or "deeper into the mine"), and flags for what's available there.
Available features might include a list of NPCs present, enemy encounter tables (random enemies that can spawn here), vendors with their inventories, quest givers, points of interest that can be examined, and any environmental hazards or special mechanics.
A location in the Fargodeep Mine might be dark (limiting combat effectiveness without a torch), have kobold and spider encounters, contain a specific named kobold boss deeper in, and have a mineable node that yields copper ore.

## ZONES

A zone groups locations together and defines the overall area. Each zone has a name, description, recommended level range, a list of all locations within it, ambient enemy types that might appear across the zone, and perhaps zone-wide modifiers like hostile weather or faction reputation effects.
Zones connect to each other at specific boundary locations — the road out of Elwynn Forest leads to Westfall, the path through Darkshire leads to Deadwind Pass.

## NPCs

NPC definitions cover anyone the player can interact with who isn't an enemy. Each NPC has a name, description, their location, dialogue options, and their functional roles.
An NPC might be a quest giver (with a list of quests they offer and the conditions for offering each), a vendor (with an inventory of items for sale and buy prices), a trainer (who teaches new abilities), a repair service, or simply flavor — a farmer who comments on the gnoll problem, a guard who warns about the mine.
Dialogue can be a simple set of lines, or a more complex tree if you want branching conversations. At minimum, the player should be able to greet the NPC and see any available quests or services.

## QUESTS

The quest structure is one of the more complex data types. Each quest has an identifier, name, description, the NPC who gives it, prerequisites (other quests that must be completed first, level requirements, etc.), objectives, rewards, and any follow-up quests it unlocks.
Objectives come in several types. Kill objectives track a count of a specific enemy type to defeat. Collection objectives require gathering a certain number of a specific item (either dropped by enemies or found in the world). Delivery objectives require bringing an item to a specific NPC. Exploration objectives require reaching a specific location. Interaction objectives require examining or using something specific.
A quest might have multiple objectives that can be completed in any order, or it might have stages where objectives unlock sequentially.
Rewards include experience, gold, choice of items (pick one of these three rewards), reputation gains, and unlocking new content.

## GAME STATE AND SAVE DATA

The game state structure captures everything needed to save and restore a game. This includes the full player data structure, the current state of all quests (which are available, active, completed), any world state changes (enemies that don't respawn once killed, doors that have been opened, NPCs that have moved or died), the current time or day cycle if you implement one, and any global flags tracking story progress.
When saving, this entire structure serializes to JSON. When loading, the game reconstructs the world from the base data files and then applies the saved state on top.

## CONFIGURATION AND BALANCE TABLES

Separate from the content data, you'll want configuration structures for game balance. This includes the experience curve (XP required per level), damage formulas (how stats translate to actual damage), loot quality distributions by zone level, vendor price multipliers, regeneration rates out of combat, and any difficulty settings.
Keeping these separate makes tuning the game much easier — you can adjust how fast players level or how much health potions restore without digging through content definitions.

## FILE ORGANIZATION

I'd suggest organizing the data files by type: a classes folder or file with all class definitions, an abilities file, an items file split into equipment, consumables, and quest items, an enemies file organized by zone, a zones folder with one file per zone containing its locations, an npcs file organized by zone, and a quests file organized by zone or quest chain.
