import csv
from models.save_file import HadesSaveFile
import gamedata # Used by export_runs_to_csv and potentially others
import copy
from pathlib import Path
from typing import Dict
import json

# Helper functions (moved from main.py)
def _easy_mode_level_from_damage_reduction(damage_reduction: int) -> int:
    # Make sure the damage reduction is between 20-80 as that is what the game uses, out of range might not be safe
    damage_reduction = max(20, min(80, damage_reduction))
    easy_mode_level = (damage_reduction - 20) / 2
    return int(easy_mode_level) # Ensure int for consistency if used as level

def _damage_reduction_from_easy_mode_level(easy_mode_level: int) -> int:
    # Easy mode level is half the amount of damage reduction added to the base damage reduction from enabling god mode
    # easy mode level 10 => 20 + (10 * 2) = 40% damage reduction
    damage_reduction = (easy_mode_level * 2) + 20
    return damage_reduction

# New functions (structure only for now)
def load_save_file(file_path: str) -> HadesSaveFile:
    """Loads a Hades save file and returns the HadesSaveFile object."""
    # Actual implementation will call HadesSaveFile.from_file(file_path)
    # and handle potential errors.
    print(f"Core logic: Loading {file_path}")
    save_file = HadesSaveFile.from_file(file_path)
    return save_file

def save_game_file(save_file_object: HadesSaveFile, target_path: str):
    """Saves the HadesSaveFile object to the target path."""
    # Actual implementation will call save_file_object.to_file(target_path)
    print(f"Core logic: Saving to {target_path}")
    save_file_object.to_file(target_path)

def get_save_info(save_file_object: HadesSaveFile) -> dict:
    """Extracts general save information."""
    # Extracts info like version, runs, location, god/hell mode status
    print("Core logic: Getting save info")
    return {
        "version": save_file_object.version,
        "runs": save_file_object.runs,
        "location": save_file_object.location,
        "god_mode_enabled": save_file_object.god_mode_enabled,
        "hell_mode_enabled": save_file_object.hell_mode_enabled,
        "easy_mode_level": save_file_object.lua_state.easy_mode_level, # For god_mode_reduction
    }

def get_currencies(save_file_object: HadesSaveFile) -> dict:
    """Extracts currency data from the save file object."""
    # Extracts Darkness, Gems, Diamonds etc. from save_file_object.lua_state
    print("Core logic: Getting currencies")
    ls = save_file_object.lua_state
    return {
        "darkness": ls.darkness,
        "gems": ls.gems,
        "diamonds": ls.diamonds,
        "nectar": ls.nectar,
        "ambrosia": ls.ambrosia,
        "chthonic_key": ls.chthonic_key,
        "money": ls.money,
        "titan_blood": ls.titan_blood,
    }


BOON_LIST_FILE = Path("boon_list.json")    

def load_boon_list() -> Dict:
    if BOON_LIST_FILE.exists():
        with open(BOON_LIST_FILE, "r") as f:
            return json.load(f)
    return {}

def save_boon_list(boon_list: Dict):
    with open(BOON_LIST_FILE, "w") as f:
        json.dump(boon_list, f, indent=4)

def deep_copy_dict(obj):
    # Recursive deep copy without using copy.deepcopy
    if isinstance(obj, dict):
        return {k: deep_copy_dict(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [deep_copy_dict(item) for item in obj]
    else:
        return obj

def get_boons(save_file_object) -> Dict[str, str]:
    print("Core logic: Getting Boons")
    boons = save_file_object.lua_state.boons  # dict of boon_name -> { "1.0": {...} }
    boon_list = load_boon_list()
    result = {}

    for boon_name, boon_data in boons.items():
        # print("Checking boon : " + boon_name);
        data = boon_data.get(1, {})

        level = data.get("OldLevel")
        result[boon_name] = f"Lv {int(level)}" if level is not None else "Lv Max"

        if boon_name not in boon_list:
            boon_list[boon_name] = deep_copy_dict(boon_data)
            print(f"New boon discovered and added to boon_list: {boon_name}")

    save_boon_list(boon_list)
    return result



def update_boon_level(save_file_object, boon_name: str, level: int) -> None:
    print(f"Updating boon '{boon_name}' to level {level}")
    boons = save_file_object.lua_state.boons

    if boon_name not in boons:
        # If the boon doesn't exist yet, initialize its structure
        boons[boon_name] = {1: {"OldLevel": level}}
        print(f"Added new boon '{boon_name}' with level {level}")
    else:
        # Update existing boon's level
        boons[boon_name].setdefault(1, {})["OldLevel"] = level
        print(f"Set level {level} for existing boon '{boon_name}'")

def remove_boon(save_file_object, boon_name: str) -> None:
    print(f"Removing boon '{boon_name}'")
    boons = save_file_object.lua_state.boons

    if boon_name in boons:
        del boons[boon_name]
        print(f"Boon '{boon_name}' removed successfully")
    else:
        print(f"Boon '{boon_name}' not found; nothing to remove")

def add_boon(save_file_object):
    boon_list = load_boon_list()
    if not boon_list:
        print("No boons in boon_list to add.")
        return

    print("Available boons:")
    boon_names = list(boon_list.keys())
    for i, name in enumerate(boon_names, 1):
        print(f"{i}. {name}")

    try:
        choice = int(input("Enter the number of the boon to add: ")) - 1
        if 0 <= choice < len(boon_names):
            boon_name = boon_names[choice]
            base_data = deep_copy_dict(boon_list[boon_name])

            # The base_data is expected to be in the form {1: { ... }}
            if 1 not in base_data:
                base_data[1] = {}

            level = base_data[1].get("OldLevel", "Max")
            change = input(f"Current level is {level}. Change it? (y/n): ").lower()
            if change == "y":
                new_level = input("Enter new level (leave blank for Max): ")
                if new_level.strip() == "":
                    base_data[1].pop("OldLevel", None)  # Max level
                else:
                    base_data[1]["OldLevel"] = int(new_level)

            # Add or replace the boon in the save file
            save_file_object.lua_state.boons[boon_name] = base_data
            print(f"Boon '{boon_name}' added to save file.")
        else:
            print("Invalid selection.")
    except ValueError:
        print("Please enter a valid number.")

    
    
    
def update_lua(save_file_object: HadesSaveFile):
    embed()

def update_field(save_file_object: HadesSaveFile, field_name: str, field_value: any):
    """Updates a specific field in the save file object's lua_state."""
    # Logic to map field_name to the correct attribute in save_file_object.lua_state
    # and update it. Will need type conversion for numeric values.
    # Also handles special cases like 'god_mode_reduction' and 'hell_mode'.
    print(f"Core logic: Updating {field_name} to {field_value}")
    ls = save_file_object.lua_state
    if field_name == "darkness":
        ls.darkness = float(field_value)
    elif field_name == "gems":
        ls.gems = float(field_value)
    elif field_name == "money":
        ls.money = float(field_value)
    elif field_name == "diamonds":
        ls.diamonds = float(field_value)
    elif field_name == "nectar":
        ls.nectar = float(field_value)
    elif field_name == "ambrosia":
        ls.ambrosia = float(field_value)
    elif field_name == "keys": # Internal name is chthonic_key
        ls.chthonic_key = float(field_value)
    elif field_name == "titan_blood":
        ls.titan_blood = float(field_value)
    elif field_name == "god_mode_reduction":
        # Convert percentage to easy_mode_level
        ls.easy_mode_level = _easy_mode_level_from_damage_reduction(float(field_value))
    elif field_name == "hell_mode":
        is_hell_mode = str(field_value).lower() in ['true', 'on', '1', 'yes']
        ls.hell_mode = is_hell_mode
        save_file_object.hell_mode_enabled = is_hell_mode # Also update this top-level flag
    elif field_name == "boons":
        while True:
            print("\n--- Boon Management ---")
            print("1. List current boons")
            print("2. Add a boon")
            print("3. Remove a boon")
            print("4. Update boon level")
            print("5. Exit boon manager")
            choice = input("Choose an option (1-5): ").strip()

            if choice == "1":
                current_boons = ls.boons
                if not current_boons:
                    print("No boons currently in save file.")
                else:
                    for name, data in current_boons.items():
                        level = data.get(1, {}).get("OldLevel")
                        level_display = f"Lv {int(level)}" if level is not None else "Lv Max"
                        print(f"- {name}: {level_display}")

            elif choice == "2":
                add_boon(save_file_object)

            elif choice == "3":
                name = input("Enter the name of the boon to remove: ").strip()
                remove_boon(save_file_object, name)

            elif choice == "4":
                name = input("Enter the name of the boon to update: ").strip()
                if name not in ls.boons:
                    print(f"Boon '{name}' not found.")
                    continue
                new_level = input("Enter new level (leave blank for Max): ").strip()
                if new_level == "":
                    ls.boons[name][1].pop("OldLevel", None)
                    print(f"Set '{name}' to Lv Max.")
                else:
                    try:
                        level_int = int(new_level)
                        update_boon_level(save_file_object, name, level_int)
                        print(f"Updated '{name}' to level {level_int}.")
                    except ValueError:
                        print("Invalid level. Must be an integer.")

            elif choice == "5":
                print("Exiting boon manager.")
                break
            else:
                print("Invalid choice. Please enter a number from 1 to 5.")

        
    else:
        raise ValueError(f"Unknown field: {field_name}")

def reset_npc_gifts(save_file_object: HadesSaveFile):
    """Resets NPC gift records in the save file object."""
    # Mirrors logic from App.reset_gift_record()
    print("Core logic: Resetting NPC gifts")
    ls = save_file_object.lua_state
    ls.gift_record = {}
    ls.npc_interactions = {}
    ls.trigger_record = {}
    ls.activation_record = {}
    ls.use_record = {}
    ls.text_lines = {}

# Copied _get_aspect_from_trait_cache and _get_weapon_from_weapons_cache from main.py App class
# These are needed for export_runs_to_csv
def _get_aspect_from_trait_cache(trait_cache):
    for trait in trait_cache:
        if trait in gamedata.AspectTraits:
            return f"Aspect of {gamedata.AspectTraits[trait]}"
    return "Redacted"

def _get_weapon_from_weapons_cache(weapons_cache):
    for weapon_name in gamedata.HeroMeleeWeapons.keys():
        if weapon_name in weapons_cache:
            return gamedata.HeroMeleeWeapons[weapon_name]
    return "Unknown weapon"

def export_runs_to_csv(save_file_object: HadesSaveFile, csv_filepath: str):
    """Exports run history from the save file object to a CSV file."""
    # Mirrors logic from App.export_runs_as_csv()
    # Uses _get_aspect_from_trait_cache, _get_weapon_from_weapons_cache, 
    # and _damage_reduction_from_easy_mode_level helper functions.
    print(f"Core logic: Exporting runs to {csv_filepath}")
    
    runs_data = save_file_object.lua_state.to_dicts() # This returns a list
    if not runs_data or "GameState" not in runs_data[0] or "RunHistory" not in runs_data[0]["GameState"]:
        print("Error: Could not find RunHistory in save file.")
        return

    runs = runs_data[0]["GameState"]["RunHistory"]

    with open(csv_filepath, "w", newline='') as csvfile:
      run_writer = csv.writer(csvfile, dialect='excel')
      run_writer.writerow([
          "Attempt", "Heat", "Weapon", "Form", 
          "Elapsed time (seconds)", "Outcome", "Godmode", 
          "Godmode damage reduction"
      ])

      for key, run in runs.items():
          run_writer.writerow([
              # Attempt
              int(key),
              # Heat
              run.get("ShrinePointsCache", ""),
              # Weapon
              _get_weapon_from_weapons_cache(run["WeaponsCache"]) if "WeaponsCache" in run else "",
              # Form
              _get_aspect_from_trait_cache(run["TraitCache"]) if "TraitCache" in run else "",
              # Run duration (seconds)
              run.get("GameplayTime", ""),
              # Outcome
              "Escaped" if run.get("Cleared", False) else "",
              # Godmode
              "EasyModeLevel" in run,
              # Godmode damage reduction
              _damage_reduction_from_easy_mode_level(run["EasyModeLevel"]) if "EasyModeLevel" in run else ""
          ])
    print(f"Successfully exported runs to {csv_filepath}")
