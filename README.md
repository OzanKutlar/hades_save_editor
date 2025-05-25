# Pluto: Hades Save Editor CLI

Pluto is a command-line tool for viewing and editing save files for the game Hades. This tool allows you to modify various aspects of your save data, such as currencies, character stats, and more, directly from your terminal.

This project was converted from an earlier GUI-based Hades save editor.

## Features (Current & Planned)

*   View general save information (version, run count, location).
*   Display and update in-game currencies (Darkness, Gems, Diamonds, Nectar, Ambrosia, Keys, Titan Blood).
*   Modify God Mode damage reduction.
*   Enable/Disable Hell Mode.
*   Reset NPC gift records.
*   Export run history to a CSV file.

## Getting Started

### Prerequisites

*   Python 3.7+
*   pip (Python package installer)

### Installation

1.  Clone this repository or download the source code:
    ```bash
    git clone https://github.com/your-username/hades-save-editor-cli.git # Replace with actual repo URL if known
    cd hades-save-editor-cli
    ```
    (If you downloaded a zip, extract it and navigate into the project directory.)

2.  (Optional but Recommended) Create and activate a virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3.  Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Basic Usage

All commands are run using `pluto_cli.py`. You must provide the path to your Hades save file using the `--file` (or `-f`) argument for most operations. Hades save files are typically named `ProfileX.sav` (e.g., `Profile1.sav`) and can be found in your Documents folder under `Saved Games\Hades`.

### General Help

To see the list of all available commands and general options:
```bash
python pluto_cli.py --help
```

To get help for a specific command, use `python pluto_cli.py <command> --help`. For example:
```bash
python pluto_cli.py update --help
```

### Examples

Replace `<your_save.sav>` with the actual path to your save file (e.g., `Profile1.sav` or `C:\Users\YourName\Documents\Saved Games\Hades\Profile1.sav`).

**1. Show Save File Information:**
Displays general info like version, run count, and current location.
```bash
python pluto_cli.py --file <your_save.sav> show info
```

**2. Show Currencies:**
Displays current amounts of Darkness, Gems, Diamonds, etc.
```bash
python pluto_cli.py --file <your_save.sav> show currencies
```

**3. Update a Value:**
Changes the amount of a currency or a specific field. For example, to set Darkness to 10000:
```bash
python pluto_cli.py --file <your_save.sav> update darkness 10000
```
This will overwrite the original save file.

**4. Update and Save to a New File:**
To update a value and save the changes to a new file (leaving the original untouched), use the `--output` (or `-o`) option. For example, to set Titan Blood to 50 and save to `Profile1_mod.sav`:
```bash
python pluto_cli.py --file <your_save.sav> update titan_blood 50 --output <new_save.sav>
```
(e.g., `python pluto_cli.py --file Profile1.sav update titan_blood 50 --output Profile1_mod.sav`)

**5. Reset NPC Gifts:**
Resets all NPC gift progress.
```bash
python pluto_cli.py --file <your_save.sav> reset_gifts
```
You can also use `--output` to save to a new file.

**6. Export Run History to CSV:**
Exports your completed run history into a CSV file.
```bash
python pluto_cli.py --file <your_save.sav> export_runs user_runs.csv
```
This will create `user_runs.csv` in the current directory with your run data.

## Disclaimer

Modifying game save files can potentially lead to corrupted saves or unexpected behavior in your game. Always back up your original save files before making any changes. Use this tool at your own risk.
The developers are not responsible for any damage or loss of data.
