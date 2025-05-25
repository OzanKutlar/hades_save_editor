import csv
from models.save_file import HadesSaveFile
import gamedata # Used by export_runs_to_csv and potentially others
from IPython import embed

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
    

def get_loot_choices(save_file_object: HadesSaveFile) -> dict:
    print("Core logic: Getting Boons")
    loot_choices = save_file_object.loot_choice
    choice_counts = {}

    for key, upgrade in loot_choices.items():
        for _, choice in upgrade.get("UpgradeChoices", {}).items():
            if choice.get("Chosen", "false") == "true":
                name = choice.get("Name")
                if name:
                    choice_counts[name] = choice_counts.get(name, 0) + 1

    # Format result like: "TraitName - Lv X"
    return {name: f"Lv {level}" for name, level in choice_counts.items()}



def duplicate_choice(save_file_object: HadesSaveFile, trait_name: str) -> None:
    loot_choices = save_file_object.loot_choice
    for upgrade_key, upgrade in loot_choices.items():
        choices = upgrade.get("UpgradeChoices", {})
        for choice in choices.values():
            if choice.get("Chosen", "true") == "true" and choice.get("Name") == trait_name:
                # Duplicate the upgrade into a new entry
                new_upgrade = copy.deepcopy(upgrade)
                max_key = max(float(k) for k in loot_choices.keys()) + 1.0
                loot_choices[str(max_key)] = new_upgrade
                return  # Only duplicate once


def add_choice(save_file_object: HadesSaveFile, trait_name: str) -> None:
    loot_choices = save_file_object.loot_choice
    if not loot_choices:
        return

    upgrade_keys = list(loot_choices.keys())
    random_upgrade_key = random.choice(upgrade_keys)
    upgrade = loot_choices[random_upgrade_key]
    choices = upgrade.get("UpgradeChoices", {})

    # Pick a random key from choices to replace
    choice_keys = list(choices.keys())
    if not choice_keys:
        return

    replace_key = random.choice(choice_keys)

    # Unchoose all current choices in this upgrade
    for choice in choices.values():
        choice["Chosen"] = "false"

    # Replace the selected choice with new trait
    choices[replace_key] = {
        "Rarity": "Common",  # Default rarity
        "Chosen": "true",
        "Name": trait_name
    }    

def remove_choice(save_file_object: HadesSaveFile, trait_name: str) -> None:
    loot_choices = save_file_object.loot_choice
    # Filter out entries where the trait was chosen
    filtered_upgrades = []

    for key in sorted(loot_choices.keys(), key=float):
        upgrade = loot_choices[key]
        choices = upgrade.get("UpgradeChoices", {})

        # Check if this upgrade has the trait chosen
        remove = False
        for choice in choices.values():
            if choice.get("Chosen", "false") == "true" and choice.get("Name") == trait_name:
                remove = True
                break

        if not remove:
            filtered_upgrades.append(upgrade)

    # Rebuild the loot_choice with updated contiguous keys
    new_loot_choices = {}
    for index, upgrade in enumerate(filtered_upgrades):
        new_key = f"{float(index):.1f}"
        new_loot_choices[new_key] = upgrade

    save_file_object.loot_choice = new_loot_choices

    
    
    
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
        print("Entering Boon Modification Mode...")
        while True:
            print("\nChoose an option:")
            print("  1. View current chosen boons")
            print("  2. Remove a boon")
            print("  3. Duplicate a boon")
            print("  4. Add a new boon")
            print("  5. Exit")
            choice = input("Enter your choice [1-5]: ").strip()

            if choice == "1":
                boons = get_loot_choices(save_file_object)
                print("Chosen Boons:")
                for boon, level in boons.items():
                    print(f"  {boon}: {level}")

            elif choice == "2":
                boon_name = input("Enter the exact name of the boon to remove: ").strip()
                remove_choice(save_file_object, boon_name)
                print(f"Removed all instances of '{boon_name}' that were chosen.")

            elif choice == "3":
                boon_name = input("Enter the exact name of the boon to duplicate: ").strip()
                duplicate_choice(save_file_object, boon_name)
                print(f"Duplicated one instance of '{boon_name}'.")

            elif choice == "4":
                boon_name = input("Enter the exact name of the new boon to add and mark as chosen: ").strip()
                add_choice(save_file_object, boon_name)
                print(f"Added '{boon_name}' as a new chosen boon.")

            elif choice == "5":
                print("Exiting Boon Modification Mode.")
                break
            else:
                print("Invalid input. Please enter a number between 1 and 5.")
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
