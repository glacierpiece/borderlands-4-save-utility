# Borderlands 4 Save Encrypter and Decrypter

A tool to decrypt and encrypt Borderlands 4 save files for editing, with advanced item serial decoding/encoding capabilities for modifying weapon and equipment stats. Feel free to use this code in any way you see fit, just credit me! Enjoy.

### If you find this tool helpful, please consider giving it a ⭐!

## Requirements

- [uv](https://docs.astral.sh/uv/getting-started/installation/) - Python package and project manager (handles Python installation and dependencies automatically)

*Alternative: Any tool that supports [PEP 723](https://peps.python.org/pep-0723/) inline script metadata (like `pipx run` with recent versions)*

## Installation

No installation needed! The script is self-contained and will automatically install its dependencies when first run.

## Usage

### View Help

To see detailed usage information with examples:

```bash
uv run blcrypt.py decrypt --help
uv run blcrypt.py encrypt --help
```

*Or if you made the script executable: `./blcrypt.py decrypt --help`*

### Save Decrypt/Encrypt 

Convert a `.sav` file to editable YAML:

```bash
uv run blcrypt.py decrypt -in 1.sav -out save.yaml -id YOUR_STEAM_ID
```

Edit the YAML file in any text editor and modify the values you want to change.

Convert the edited YAML back to a `.sav` file:

```bash
uv run blcrypt.py encrypt -in save.yaml -out 1.sav -id YOUR_STEAM_ID
```

### Save Decrypt/Encrypt with Item Serial Decoding/Encoding (EXPERIMENTAL)

#### Step 1: Decrypt with Item Serial Decoding 

This will decode item serials and add an editable `_DECODED_ITEMS` section to your YAML file. **Important**: The output contains the complete save file as YAML plus the decoded items section.

```bash
uv run blcrypt.py decrypt -in 1.sav -out save.yaml -id YOUR_STEAM_ID --decode-serials
```

The generated YAML will include your **complete save file** plus a `_DECODED_ITEMS` section like this:

```yaml
_DECODED_ITEMS:
  inventory.items[0].serial:
    original_serial: "@Ugr..."
    item_type: "r"
    category: "weapon"
    confidence: "high"
    stats:
      primary_stat: 1234     # Weapon damage - edit this!
      secondary_stat: 5678   # Secondary stats - edit this!
      rarity: 12            # Rarity level - edit this!
      manufacturer: 123     # Manufacturer ID - edit this!
      item_class: 123       # Weapon class - edit this!
```

#### Step 2: Edit Item Stats

Modify the values in the `_DECODED_ITEMS` section:
- **primary_stat**: Main weapon damage/equipment power
- **secondary_stat**: Secondary weapon/equipment stats
- **rarity**: Item rarity level (affects item quality - common, uncommon, rare, etc.)
- **manufacturer**: Weapon/equipment manufacturer
- **item_class**: Specific weapon/equipment type
- **level**: Item level (when available)

#### Step 3: Encrypt with Item Serial Encoding

This will read the complete YAML file, apply your changes from `_DECODED_ITEMS` back to the item serials, remove the `_DECODED_ITEMS` section, and encrypt the complete save file to be used in game:

```bash
uv run blcrypt.py encrypt -in save.yaml -out 1_modified.sav -id YOUR_STEAM_ID --encode-serials
```

## Supported Item Types

The decoder can handle multiple item categories with different confidence levels:

- **Weapons** (@Ugr): High confidence decoding of damage, rarity, manufacturer
- **Equipment** (@Uge): High/medium confidence decoding of stats and properties
- **Equipment Alt** (@Ugd): High/medium confidence for alternative equipment types
- **Special Items** (@Ugw, @Ugu, @Ugf, @Ug!): Low confidence generic decoding

Items with "high" confidence are most reliable for editing. "Medium" and "low" confidence items may work but are less predictable for now, I'll get to it when I get to it.

## Complete Workflow Example

### Basic Save Editing

For basic save editing without modifying item stats:

```bash
# 1. Decrypt save file to YAML
uv run blcrypt.py decrypt -in 1.sav -out save.yaml -id 76561198XXXXXXXXX

# 2. Edit save.yaml in any text editor

# 3. Encrypt back to save file
uv run blcrypt.py encrypt -in save.yaml -out 1.sav -id 76561198XXXXXXXXX

# 4. Replace your original save file with 1.sav
```

### Advanced Save Editing with Item Serial Modification (EXPERIMENTAL)

```bash
# 1. Decrypt save file with item serial decoding
uv run blcrypt.py decrypt -in 1.sav -out save.yaml -id 76561198XXXXXXXXX --decode-serials

# 2. Edit the _DECODED_ITEMS section in save.yaml to modify weapon damage, rarity, etc.

# 3. Encrypt back with item serial encoding
uv run blcrypt.py encrypt -in save.yaml -out 1.sav -id 76561198XXXXXXXXX --encode-serials

# 4. Replace your original save file with the new 1.sav
```

## Important Notes

### ONLY STEAM SAVES ARE SUPPORTED (FOR NOW)

- **Backup your save files** before using this tool
- Your Steam ID is the 17-digit number that starts with `7656119...`
- On Windows, you can find this ID as the folder location: `C:\Users\{username}\Documents\My Games\Borderlands 4\Saved\SaveGames` - the folder name in here is the ID to use
- The Steam ID **MUST** match the original save file owner
- If you get PKCS7 or zlib errors, verify your Steam ID is correct
- Encrypt/decrypt the **NUMBERED** or **PROFILE** saves depending on what you want to edit (1.sav, 2.sav, etc. vs. Profile.sav). **#.sav** (numbered) is full save. **Profile.sav** has cosmetics.
- When editing item stats (in **NUMBERED** saves), keep values within reasonable ranges first
- **High** confidence items are most reliable for stat modifications
- The `_DECODED_ITEMS` section is automatically removed during encryption
- Open an issue if you're having trouble and maybe I or someone else will assist/troubleshoot

## Command Summary

```bash
# Basic decrypt/encrypt (no item modification)
uv run blcrypt.py decrypt -in 1.sav -id 76561198XXXXXXXXX
uv run blcrypt.py encrypt -in 1.yaml -id 76561198XXXXXXXXX

# Advanced: Decode item serials for editing
uv run blcrypt.py decrypt -in 1.sav -id 76561198XXXXXXXXX --decode-serials

# Advanced: Encode modified item serials back to save
uv run blcrypt.py encrypt -in 1.yaml -id 76561198XXXXXXXXX --encode-serials
```

## Troubleshooting

- **"PKCS7 padding error"**: Wrong Steam ID
- **"zlib decompression error"**: Wrong Steam ID or corrupted file
- **File size not multiple of 16**: File may be corrupted or not a valid BL4 save file

## License

MIT License

Copyright (c) 2025

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.








