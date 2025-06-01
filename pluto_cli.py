import argparse
import sys
import os # For checking file existence in export_runs
import tempfile
import click # Added for click.edit()
import subprocess
import json

from models.raw_save_file import RawSaveFile # Changed import
from models.lua_state import LuaState, lua_state_to_json_string, json_string_to_lua_state_data
from lua_editor import LuaStateEditor # Added import
from core_logic import (
    load_save_file,
    save_game_file,
    update_lua,
    get_save_info,
    get_currencies,
    get_boons,
    update_field,
    reset_npc_gifts,
    export_runs_to_csv,
    _damage_reduction_from_easy_mode_level # For displaying god mode reduction
)

def handle_edit_raw(args):
    # Give the user a moment to read the warning or a chance to Ctrl+C
    try:
        input("Press Enter to continue, or Ctrl+C to abort...")
    except KeyboardInterrupt:
        print("\nOperation aborted by user.")
        return

    save_file_path = args.file
    temp_file_name = None  # Ensure temp_file_name is defined for the finally block

    try:
        try:
            print(f"Loading save file: '{save_file_path}'...")
            raw_save_file = RawSaveFile.from_file(save_file_path) # Changed to RawSaveFile
            print("Save file loaded successfully.")
        except FileNotFoundError:
            print(f"Error: Save file not found at '{save_file_path}'. Please verify the path and try again.", file=sys.stderr)
            return 
        except IOError as e:
            print(f"Error: Could not read the save file at '{save_file_path}'. An IO error occurred: {e}", file=sys.stderr)
            return 
        except Exception as e: 
            print(f"Error: An unexpected error occurred while loading the save file '{save_file_path}': {e}", file=sys.stderr)
            return

        try:
            print("Preparing save data for JSON conversion...")
            # raw_save_file.save_data is a construct.Container
            # Create a dictionary for JSON editing
            editable_save_data_dict = {}
            
            # Define expected fields based on common schema structure (e.g., sav16)
            # This list should be comprehensive for all supported versions or handled dynamically.
            # For now, using a list similar to what was in RawSaveFile previously.
            fields_to_copy = [
                "version", "location", "runs", "active_meta_points",
                "active_shrine_points", "god_mode_enabled", "hell_mode_enabled",
                "lua_keys", "current_map_name", "start_next_map" 
                # "lua_state" is handled separately
                # "timestamp" is version-specific (only in v16's save_data container)
            ]
            if raw_save_file.version == 16 and hasattr(raw_save_file.save_data, "timestamp"):
                fields_to_copy.insert(1, "timestamp")

            for field_name in fields_to_copy:
                if hasattr(raw_save_file.save_data, field_name):
                    editable_save_data_dict[field_name] = getattr(raw_save_file.save_data, field_name)
                else:
                    # Handle cases where a field might not exist (e.g. older versions)
                    # For simplicity, we assume fields exist if listed, or use None/default.
                    editable_save_data_dict[field_name] = None 
                    print(f"Warning: Field '{field_name}' not found in save_data Container for version {raw_save_file.version}. Setting to None in JSON.", file=sys.stderr)

            # Handle lua_state: convert from bytes/ListContainer to list of dicts
            lua_state_from_container = raw_save_file.save_data.lua_state
            if isinstance(lua_state_from_container, list): # If it's ListContainer
                lua_state_from_container = bytes(lua_state_from_container)
            
            if isinstance(lua_state_from_container, bytes):
                lua_state_obj = LuaState.from_bytes(raw_save_file.version, lua_state_from_container)
                editable_save_data_dict['lua_state'] = lua_state_obj.to_dicts()
            else:
                print(f"Warning: 'lua_state' in save_data Container was not bytes or list, but type {type(lua_state_from_container)}. Setting to None in JSON.", file=sys.stderr)
                editable_save_data_dict['lua_state'] = None
            
            json_string = json.dumps(editable_save_data_dict, indent=2)
            print("Save data successfully converted to JSON.")
        except Exception as e:
            print(f"Error: Failed to convert save data to JSON. Details: {e}", file=sys.stderr)
            return


        try:
            # Create the temporary file
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as tmp_file:
                temp_file_name = tmp_file.name
                tmp_file.write(json_string)
            print(f"JSON data has been written to a temporary file: {temp_file_name}")
        except (IOError, OSError) as e:
            print(f"Error: Could not create or write to the temporary file. Details: {e}", file=sys.stderr)
            if temp_file_name and os.path.exists(temp_file_name): 
                 os.remove(temp_file_name)
            return 

        editor = os.environ.get('EDITOR')
        editor_cmd_list = [] # Renamed for clarity
        editor_opened_successfully = False
        if not editor:
            if sys.platform == "win32":
                # Try to use Notepad++ instead of Notepad
                notepad_plus_plus_path = r"C:\Program Files\Notepad++\notepad++.exe"
                if os.path.exists(notepad_plus_plus_path):
                    editor_cmd_list = [notepad_plus_plus_path, '-multiInst', '-nosession']
                else:
                    editor_cmd_list = ['notepad']  # Fallback
            elif sys.platform == "darwin":
                editor_cmd_list = ['open', '-W']  # -W waits for app to close
            else: # Linux and other Unix-like
                # Try common terminal editors if EDITOR is not set
                # Check for availability in a real scenario might be needed
                # For now, stick to xdg-open as a general fallback
                editor_cmd_list = ['xdg-open']
        else:
            editor_cmd_list = editor.split() # Allow for editor commands with arguments
        
        editor_cmd_list.append(temp_file_name)

        try:
            print(f"Attempting to open the temporary file with your editor: {' '.join(editor_cmd_list)}")
            print("Waiting for you to close the editor...")
            
            # For xdg-open, it often returns immediately. This is a known limitation.
            # Other editors like nano, vim, gedit, when called directly, will block.
            # Notepad on Windows when called directly also blocks.
            # 'open -W' on macOS blocks.
            if editor_cmd_list[0] == 'xdg-open':
                # For xdg-open, we can't reliably wait. Inform the user.
                print("INFO: 'xdg-open' may return immediately. Please ensure you save and close the file in your editor before proceeding.")
                subprocess.run(editor_cmd_list) # Not using check=True as xdg-open exit status is not always reliable
                input("Press Enter here after you have saved and closed the editor...")
            elif editor_cmd_list[0] == 'notepad' and sys.platform == 'win32' and len(editor_cmd_list) == 2 : # just 'notepad <file>'
                # `subprocess.run(['notepad', temp_file_name], check=True)` blocks.
                # The previous `cmd /C start /WAIT notepad` is also fine. Sticking to direct call for simplicity.
                subprocess.run(editor_cmd_list, check=True)
            else: # General case for $EDITOR, 'open -W', or direct terminal editors
                subprocess.run(editor_cmd_list, check=True)
            editor_opened_successfully = True
        except FileNotFoundError:
            print(f"Error: Editor command '{editor_cmd_list[0]}' not found. Please ensure your EDITOR environment variable is set correctly, or that the default editor is available in your PATH.", file=sys.stderr)
            return 
        except subprocess.CalledProcessError as e:
            print(f"Error: Your editor exited with an error (code: {e.returncode}). Please check any messages from the editor.", file=sys.stderr)
            # Proceeding, as user might have saved, or the error might be non-critical for the file itself.
            editor_opened_successfully = True # It opened, even if it error'd on close
        except Exception as e: 
            print(f"An unexpected error occurred while trying to open or run the editor: {e}", file=sys.stderr)
            return # If editor failed to even attempt opening, abort.
        
        if not editor_opened_successfully and not (editor_cmd_list[0] == 'xdg-open'): # xdg-open case handled by input()
             # If editor failed to open and it wasn't xdg-open (which we can't reliably track),
             # then don't proceed.
            print("Aborting due to editor failing to start properly.", file=sys.stderr)
            return

        try:
            print(f"Reading modified JSON data from temporary file: {temp_file_name}...")
            with open(temp_file_name, 'r') as tmp_file:
                modified_json_string = tmp_file.read()
            
            if not modified_json_string.strip() and temp_file_name : # Check if file is empty or just whitespace
                print("Warning: The temporary file appears to be empty or contains only whitespace. If you proceed, this might clear parts of your save data or cause errors.", file=sys.stderr)
                user_confirmation = input("Do you want to proceed with the empty data? (yes/no): ").strip().lower()
                if user_confirmation != 'yes':
                    print("Operation aborted by user. No changes will be applied.")
                    return
        except (IOError, OSError) as e:
            print(f"Error: Could not read from the temporary file '{temp_file_name}'. Details: {e}", file=sys.stderr)
            return
        exit()
        try:
            print("Parsing modified JSON data...")
            modified_data_dict = json.loads(modified_json_string)
            print("JSON data successfully parsed.")
        except json.JSONDecodeError as e:
            print(f"Error: The modified data is not valid JSON. Please correct the syntax. Details: {e}", file=sys.stderr)
            print(f"Your modified (invalid) JSON data was left in the temporary file: {temp_file_name}", file=sys.stderr)
            print("Tip: You can try opening this file in a text editor that highlights JSON errors to find the issue.", file=sys.stderr)
            # Intentionally do not remove the temp_file_name here so the user can recover their work.
            # The finally block needs to be aware of this decision if we want to persist it.
            # For now, the finally block will still remove it. This needs refinement if data persistence is key.
            # A flag could be set: e.g., `keep_temp_file_on_error = True`
            return

        try:
            print("Updating internal save data structure with modified data...")
            # Update the fields of the original raw_save_file.save_data Container
            final_lua_bytes = None
            if 'lua_state' in modified_data_dict and isinstance(modified_data_dict['lua_state'], list):
                version_for_lua_state = modified_data_dict.get('version', raw_save_file.version)
                lua_state_obj = LuaState.from_dict(version_for_lua_state, modified_data_dict['lua_state'])
                final_lua_bytes = lua_state_obj.to_bytes()

            for key, value in modified_data_dict.items():
                if key == 'lua_state':
                    if final_lua_bytes is not None:
                        setattr(raw_save_file.save_data, key, final_lua_bytes)
                elif hasattr(raw_save_file.save_data, key):
                    setattr(raw_save_file.save_data, key, value)
                # else: field in JSON not in original save_data container, might be an error or new field.
                # For now, only update existing fields.
            
            # Critically, update raw_save_file.lua_state_bytes as well
            if final_lua_bytes is not None:
                 raw_save_file.lua_state_bytes = final_lua_bytes
            
            # Note: raw_save_file.save_data (the Container) has been updated directly.
            # The assignment `raw_save_file.save_data = modified_data_dict` is no longer needed
            # as we are modifying the container in place.

            print("Internal save data (Container) updated.")
        except (TypeError, KeyError, IndexError, ValueError) as e:
            print(f"Error: The JSON data is valid, but its structure or types are not compatible with the expected save data format. Details: {e}", file=sys.stderr)
            print(f"Your modified JSON data was left in the temporary file: {temp_file_name}", file=sys.stderr)
            return
        except Exception as e:
            print(f"Error: An unexpected error occurred while updating the internal save data. Details: {e}", file=sys.stderr)
            return

        try:
            output_path = args.output if args.output else save_file_path
            print(f"Attempting to save all changes to: '{output_path}'...")
            save_game_file(raw_save_file, output_path)
            # raw_save_file.to_file(output_path) # Use RawSaveFile.to_file
            print(f"Successfully saved changes to '{output_path}'.")
            if output_path != save_file_path:
                print(f"Original file '{save_file_path}' remains unchanged.")
        except (IOError, OSError) as e:
            print(f"Error: Could not write changes back to the save file '{output_path}'. Details: {e}", file=sys.stderr)
            return
        except Exception as e:
            print(f"Error: An unexpected error occurred while saving the final changes to '{output_path}'. Details: {e}", file=sys.stderr)
            return

    except Exception as e:
        print(f"A critical unexpected error occurred during the 'edit_raw' process: {e}", file=sys.stderr)
        print("Please report this error if it seems like a bug in the tool.", file=sys.stderr)
    finally:
        # Consider a flag here if we decide to keep temp_file_name on json.JSONDecodeError
        if temp_file_name and os.path.exists(temp_file_name):
            try:
                os.remove(temp_file_name)
                print(f"Temporary file '{temp_file_name}' has been removed.")
            except OSError as e:
                print(f"Error: Could not remove the temporary file '{temp_file_name}'. You may need to remove it manually. Details: {e}", file=sys.stderr)

def handle_edit_lua(args):
    try:
        save_file = load_save_file(args.file)
        update_lua(save_file)
        
        output_path = args.output if args.output else args.file
        save_game_file(save_file, output_path)
        print(f"Successfully updated '{args.field}' to '{args.value}'. Saved to {output_path}")

    except FileNotFoundError:
        print(f"Error: Save file not found at {args.file}", file=sys.stderr)
        sys.exit(1)
    except ValueError as ve:
        print(f"Error updating field: {ve}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
        sys.exit(1)

def handle_show(args):
    try:
        save_file = load_save_file(args.file)
        if args.section == "info":
            info = get_save_info(save_file)
            print("Save File Information:")
            print(f"  Version: {info['version']}")
            print(f"  Runs: {info['runs']}")
            print(f"  Location: {info['location']}")
            print(f"  God Mode Enabled: {'Yes' if info['god_mode_enabled'] else 'No'}")
            if info['god_mode_enabled']: # Show damage reduction only if god mode is on.
                 # easy_mode_level is already in info from get_save_info
                damage_reduction = _damage_reduction_from_easy_mode_level(info['easy_mode_level'])
                print(f"  God Mode Damage Reduction: {damage_reduction}%")
            print(f"  Hell Mode Enabled: {'Yes' if info['hell_mode_enabled'] else 'No'}")

        elif args.section == "currencies":
            currencies = get_currencies(save_file)
            print("Currencies:")
            for currency, value in currencies.items():
                print(f"  {currency.replace('_', ' ').title()}: {int(value)}")
        elif args.section == "boons":
            loot_choices = get_boons(save_file)
            print("Chosen Boons:")
            if not loot_choices:
                print("  No boons were chosen.")
            else:
                for boon, level in loot_choices.items():
                    print(f"  {boon}: {level}")        
        
    except FileNotFoundError:
        print(f"Error: Save file not found at {args.file}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
        sys.exit(1)

def handle_update(args):
    try:
        save_file = load_save_file(args.file)
        update_field(save_file, args.field, args.value)
        
        output_path = args.output if args.output else args.file
        save_game_file(save_file, output_path)
        print(f"Successfully updated '{args.field}' to '{args.value}'. Saved to {output_path}")

    except FileNotFoundError:
        print(f"Error: Save file not found at {args.file}", file=sys.stderr)
        sys.exit(1)
    except ValueError as ve:
        print(f"Error updating field: {ve}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
        sys.exit(1)

def handle_reset_gifts(args):
    try:
        save_file = load_save_file(args.file)
        reset_npc_gifts(save_file)

        output_path = args.output if args.output else args.file
        save_game_file(save_file, output_path)
        print(f"Successfully reset NPC gifts. Saved to {output_path}")

    except FileNotFoundError:
        print(f"Error: Save file not found at {args.file}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
        sys.exit(1)

def handle_export_runs(args):
    try:
        # Basic check if output directory exists, or if path is a directory
        csv_path = args.csv_filepath
        if os.path.isdir(csv_path):
            print(f"Error: CSV filepath '{csv_path}' is a directory. Please provide a full file path.", file=sys.stderr)
            sys.exit(1)
        
        # Ensure the directory for the CSV file exists
        csv_dir = os.path.dirname(csv_path)
        if csv_dir and not os.path.exists(csv_dir):
            os.makedirs(csv_dir)
            print(f"Created directory: {csv_dir}")

        save_file = load_save_file(args.file)
        export_runs_to_csv(save_file, csv_path)
        # export_runs_to_csv in core_logic already prints success message
        # print(f"Successfully exported runs to {csv_path}")
    except FileNotFoundError:
        print(f"Error: Save file not found at {args.file}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred during export: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="Pluto: Hades Save Editor CLI",
        formatter_class=argparse.RawTextHelpFormatter # Ensures help text respects newlines
    )
    parser.add_argument(
        "-f", "--file",
        required=True,
        help="Path to the Hades save file (.sav)"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands", required=True)

    # Show command
    show_parser = subparsers.add_parser("show", help="Display save file data")
    show_parser.add_argument(
        "section",
        choices=["info", "currencies", "boons"],
        help=("Which section of data to display:\n"
              "  info       - File version, run count, current location, etc.\n"
              "  currencies - Darkness, Gems, Diamonds, etc.")
    )
    show_parser.set_defaults(func=handle_show)

    # Update command
    update_parser = subparsers.add_parser("update", help="Modify a field in the save file and save changes")
    update_parser.add_argument(
        "field",
        choices=[
            "darkness", "gems", "diamonds", "nectar",
            "ambrosia", "keys", "titan_blood",
            "god_mode_reduction", "hell_mode", "money", "boons", "rerolls"
        ],
        help=("Field to modify (e.g., darkness, gems, god_mode_reduction, hell_mode).\n"
              "For god_mode_reduction, provide percentage (20-80).\n"
              "For hell_mode, use 'on' or 'off'.")
    )
    update_parser.add_argument("value", help="New value for the field")
    update_parser.add_argument(
        "-o", "--output",
        help="Optional: Path to save to a new file (otherwise overwrites original)"
    )
    update_parser.set_defaults(func=handle_update)

    # Reset gifts command
    reset_gifts_parser = subparsers.add_parser("reset_gifts", help="Reset NPC gift records and save changes")
    reset_gifts_parser.add_argument(
        "-o", "--output",
        help="Optional: Path to save to a new file (otherwise overwrites original)"
    )
    reset_gifts_parser.set_defaults(func=handle_reset_gifts)

    # Export runs command
    export_parser = subparsers.add_parser("export_runs", help="Export run history to CSV")
    export_parser.add_argument("csv_filepath", help="Path to save the CSV file (e.g., runs.csv)")
    export_parser.set_defaults(func=handle_export_runs)

    # Edit raw Lua state command
    edit_raw_parser = subparsers.add_parser(
        "edit_raw", 
        help="Edit the entire save file (including Lua state) via a temporary JSON file. "
             "WARNING: This method can corrupt data if not used carefully. "
             "Prefer 'edit_lua' for safer Lua state editing."
    )
    edit_raw_parser.add_argument(
        "-o", "--output",
        help="Optional: Path to save to a new file (otherwise overwrites original)"
    )
    edit_raw_parser.set_defaults(func=handle_edit_raw)

    # Edit Lua state command (new TUI editor)
    edit_lua_parser = subparsers.add_parser(
        "edit_lua",
        help="Interactively edit the Lua state within the save file using a TUI."
    )
    edit_lua_parser.add_argument(
        "-o", "--output",
        help="Optional: Path to save to a new file (otherwise overwrites original)."
    )
    edit_lua_parser.set_defaults(func=handle_edit_lua)

    if len(sys.argv) <= 1: # Should be 1 if only script name, or 2 if only --file without command
        parser.print_help(sys.stderr)
        sys.exit(1)
    
    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
