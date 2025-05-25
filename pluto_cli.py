import argparse
import sys
import os # For checking file existence in export_runs
import json
from core_logic import (
    load_save_file,
    save_game_file,
    get_save_info,
    get_currencies,
    update_field,
    reset_npc_gifts,
    export_runs_to_csv,
    _damage_reduction_from_easy_mode_level # For displaying god mode reduction
)

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
                
        elif args.section == "get_raw":
            print("Extracting raw save file contents...")

            raw = getattr(save_file, "raw_save_file", None)
            if raw is not None:
                try:
                    # Extract instance attributes
                    raw_dict = vars(raw)
                except TypeError:
                    # Fallback if vars() fails
                    raw_dict = {
                        attr: getattr(raw, attr)
                        for attr in dir(raw)
                        if not attr.startswith('_') and not callable(getattr(raw, attr))
                    }

                # Attempt to convert all values to serializable types
                serializable_raw = {}
                for key, value in raw_dict.items():
                    try:
                        json.dumps(value)  # Test if it's serializable
                        serializable_raw[key] = value
                    except TypeError:
                        serializable_raw[key] = str(value)  # Fallback to string

                # Write to file
                output_path = os.path.join(os.getcwd(), "raw_save_file_output.json")
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(serializable_raw, f, indent=2, ensure_ascii=False)

                print(f"Raw data saved to: {output_path}")
            else:
                print("  No raw data available.")

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
        choices=["info", "currencies", "get_raw"],
        help=("Which section of data to display:\n"
              "  info       - File version, run count, current location, etc.\n"
              "  currencies - Darkness, Gems, Diamonds, etc.\n"
              "  get_raw    - Raw unparsed save file data (for debugging)")
    )
    show_parser.set_defaults(func=handle_show)


    # Update command
    update_parser = subparsers.add_parser("update", help="Modify a field in the save file and save changes")
    update_parser.add_argument(
        "field",
        choices=[
            "darkness", "gems", "diamonds", "nectar",
            "ambrosia", "keys", "titan_blood",
            "god_mode_reduction", "hell_mode", "money"
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

    if len(sys.argv) <= 1: # Should be 1 if only script name, or 2 if only --file without command
        parser.print_help(sys.stderr)
        sys.exit(1)
    
    # Check if --file is provided before parsing to give a more specific error
    # Note: argparse 'required=True' handles this, but this is an example if needed for complex cases
    # if '--file' not in sys.argv and '-f' not in sys.argv:
    #    print("Error: --file argument is required.", file=sys.stderr)
    #    parser.print_help(sys.stderr)
    #    sys.exit(1)
        
    args = parser.parse_args()
    
    # Ensure that if a command is 'update', 'field' and 'value' are present.
    # Argparse handles this due to them not being optional.
    
    args.func(args)

if __name__ == "__main__":
    main()
