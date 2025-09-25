#!/usr/bin/env -S uv run --script
# written by glacierpiece
# https://github.com/glacierpiece/borderlands-4-save-utlity

# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "pycryptodome>=3.15.0",
#     "pyyaml>=6.0",
# ]
# ///

import argparse, sys, zlib, yaml, struct
from pathlib import Path
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from typing import Dict, List, Optional, Union
from dataclasses import dataclass

def unknown_constructor(loader, _tag_suffix, node):
    if isinstance(node, yaml.ScalarNode):
        return loader.construct_scalar(node)
    elif isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node)
    elif isinstance(node, yaml.MappingNode):
        return loader.construct_mapping(node)
    else:
        return None

yaml.add_multi_constructor('!', unknown_constructor, yaml.SafeLoader)

BASE_KEY = bytes((
    0x35, 0xEC, 0x33, 0x77, 0xF3, 0x5D, 0xB0, 0xEA,
    0xBE, 0x6B, 0x83, 0x11, 0x54, 0x03, 0xEB, 0xFB,
    0x27, 0x25, 0x64, 0x2E, 0xD5, 0x49, 0x06, 0x29,
    0x05, 0x78, 0xBD, 0x60, 0xBA, 0x4A, 0xA7, 0x87
))

@dataclass
class ItemStats:
    primary_stat: Optional[int] = None
    secondary_stat: Optional[int] = None
    level: Optional[int] = None
    rarity: Optional[int] = None
    manufacturer: Optional[int] = None
    item_class: Optional[int] = None
    flags: Optional[List[int]] = None

@dataclass
class DecodedItem:
    serial: str
    item_type: str
    item_category: str
    length: int
    stats: ItemStats
    raw_fields: Dict[str, Union[int, List[int]]]
    confidence: str

def bit_pack_decode(serial: str) -> bytes:
    if serial.startswith('@Ug'):
        payload = serial[3:]
    else:
        payload = serial

    char_map = {}
    chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=!$%&*()[]{}~`^_<>?#;'
    for i, c in enumerate(chars):
        char_map[c] = i

    bits = []
    for c in payload:
        if c in char_map:
            val = char_map[c]
            bits.extend(format(val, '06b'))

    bit_string = ''.join(bits)
    while len(bit_string) % 8 != 0:
        bit_string += '0'

    byte_data = bytearray()
    for i in range(0, len(bit_string), 8):
        byte_val = int(bit_string[i:i+8], 2)
        byte_data.append(byte_val)

    return bytes(byte_data)

def bit_pack_encode(data: bytes, prefix: str = '@Ug') -> str:
    chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=!$%&*()[]{}~`^_<>?#;'

    bit_string = ''.join(format(byte, '08b') for byte in data)

    while len(bit_string) % 6 != 0:
        bit_string += '0'

    result = []
    for i in range(0, len(bit_string), 6):
        chunk = bit_string[i:i+6]
        val = int(chunk, 2)
        if val < len(chars):
            result.append(chars[val])

    return prefix + ''.join(result)

def extract_fields(data: bytes) -> Dict[str, Union[int, List[int]]]:
    fields = {}

    if len(data) >= 4:
        fields['header_le'] = struct.unpack('<I', data[:4])[0]
        fields['header_be'] = struct.unpack('>I', data[:4])[0]

    if len(data) >= 8:
        fields['field2_le'] = struct.unpack('<I', data[4:8])[0]

    if len(data) >= 12:
        fields['field3_le'] = struct.unpack('<I', data[8:12])[0]

    stats_16 = []
    for i in range(0, min(len(data)-1, 20), 2):
        val16 = struct.unpack('<H', data[i:i+2])[0]
        fields[f'val16_at_{i}'] = val16
        if 100 <= val16 <= 10000:
            stats_16.append((i, val16))

    fields['potential_stats'] = stats_16

    flags = []
    for i in range(min(len(data), 20)):
        byte_val = data[i]
        fields[f'byte_{i}'] = byte_val
        if byte_val < 100:
            flags.append((i, byte_val))

    fields['potential_flags'] = flags

    return fields

def decode_weapon(data: bytes, serial: str) -> DecodedItem:
    fields = extract_fields(data)
    stats = ItemStats()

    if 'val16_at_0' in fields:
        stats.primary_stat = fields['val16_at_0']

    if 'val16_at_12' in fields:
        stats.secondary_stat = fields['val16_at_12']

    if 'byte_4' in fields:
        stats.manufacturer = fields['byte_4']

    if 'byte_8' in fields:
        stats.item_class = fields['byte_8']

    if 'byte_1' in fields:
        stats.rarity = fields['byte_1']

    if 'byte_13' in fields and fields['byte_13'] in [2, 34]:
        stats.level = fields['byte_13']

    confidence = "high" if len(data) in [24, 26] else "medium"

    return DecodedItem(
        serial=serial,
        item_type='r',
        item_category='weapon',
        length=len(data),
        stats=stats,
        raw_fields=fields,
        confidence=confidence
    )

def decode_equipment_e(data: bytes, serial: str) -> DecodedItem:
    fields = extract_fields(data)
    stats = ItemStats()

    if 'val16_at_2' in fields:
        stats.primary_stat = fields['val16_at_2']

    if 'val16_at_8' in fields:
        stats.secondary_stat = fields['val16_at_8']

    if 'val16_at_10' in fields and len(data) > 38:
        stats.level = fields['val16_at_10']

    if 'byte_1' in fields:
        stats.manufacturer = fields['byte_1']

    if 'byte_3' in fields:
        stats.item_class = fields['byte_3']

    if 'byte_9' in fields:
        stats.rarity = fields['byte_9']

    confidence = "high" if 'byte_1' in fields and fields['byte_1'] == 49 else "medium"

    return DecodedItem(
        serial=serial,
        item_type='e',
        item_category='equipment',
        length=len(data),
        stats=stats,
        raw_fields=fields,
        confidence=confidence
    )

def decode_equipment_d(data: bytes, serial: str) -> DecodedItem:
    fields = extract_fields(data)
    stats = ItemStats()

    if 'val16_at_4' in fields:
        stats.primary_stat = fields['val16_at_4']

    if 'val16_at_8' in fields:
        stats.secondary_stat = fields['val16_at_8']

    if 'val16_at_10' in fields:
        stats.level = fields['val16_at_10']

    if 'byte_5' in fields:
        stats.manufacturer = fields['byte_5']

    if 'byte_6' in fields:
        stats.item_class = fields['byte_6']

    if 'byte_14' in fields:
        stats.rarity = fields['byte_14']

    confidence = "high" if 'byte_5' in fields and fields['byte_5'] == 15 else "medium"

    return DecodedItem(
        serial=serial,
        item_type='d',
        item_category='equipment_alt',
        length=len(data),
        stats=stats,
        raw_fields=fields,
        confidence=confidence
    )

def decode_other_type(data: bytes, serial: str, item_type: str) -> DecodedItem:
    fields = extract_fields(data)
    stats = ItemStats()

    potential_stats = fields.get('potential_stats', [])
    if potential_stats:
        stats.primary_stat = potential_stats[0][1] if len(potential_stats) > 0 else None
        stats.secondary_stat = potential_stats[1][1] if len(potential_stats) > 1 else None

    if 'byte_1' in fields:
        stats.manufacturer = fields['byte_1']

    if 'byte_2' in fields:
        stats.rarity = fields['byte_2']

    category_map = {
        'w': 'weapon_special',
        'u': 'utility',
        'f': 'consumable',
        '!': 'special'
    }

    return DecodedItem(
        serial=serial,
        item_type=item_type,
        item_category=category_map.get(item_type, 'unknown'),
        length=len(data),
        stats=stats,
        raw_fields=fields,
        confidence="low"
    )

def decode_item_serial(serial: str) -> DecodedItem:
    try:
        data = bit_pack_decode(serial)

        if len(serial) >= 4 and serial.startswith('@Ug'):
            item_type = serial[3]
        else:
            item_type = '?'

        if item_type == 'r':
            return decode_weapon(data, serial)
        elif item_type == 'e':
            return decode_equipment_e(data, serial)
        elif item_type == 'd':
            return decode_equipment_d(data, serial)
        else:
            return decode_other_type(data, serial, item_type)

    except Exception as e:
        return DecodedItem(
            serial=serial,
            item_type='error',
            item_category='decode_failed',
            length=0,
            stats=ItemStats(),
            raw_fields={'error': str(e)},
            confidence="none"
        )

def encode_item_serial(decoded_item: DecodedItem) -> str:
    try:
        original_data = bit_pack_decode(decoded_item.serial)
        data = bytearray(original_data)

        if decoded_item.item_type == 'r':
            if decoded_item.stats.primary_stat is not None and len(data) >= 2:
                struct.pack_into('<H', data, 0, decoded_item.stats.primary_stat)
            if decoded_item.stats.secondary_stat is not None and len(data) >= 14:
                struct.pack_into('<H', data, 12, decoded_item.stats.secondary_stat)
            if decoded_item.stats.rarity is not None and len(data) >= 2:
                data[1] = decoded_item.stats.rarity
            if decoded_item.stats.manufacturer is not None and len(data) >= 5:
                data[4] = decoded_item.stats.manufacturer
            if decoded_item.stats.item_class is not None and len(data) >= 9:
                data[8] = decoded_item.stats.item_class

        elif decoded_item.item_type == 'e':
            if decoded_item.stats.primary_stat is not None and len(data) >= 4:
                struct.pack_into('<H', data, 2, decoded_item.stats.primary_stat)
            if decoded_item.stats.secondary_stat is not None and len(data) >= 10:
                struct.pack_into('<H', data, 8, decoded_item.stats.secondary_stat)
            if decoded_item.stats.manufacturer is not None and len(data) >= 2:
                data[1] = decoded_item.stats.manufacturer
            if decoded_item.stats.item_class is not None and len(data) >= 4:
                data[3] = decoded_item.stats.item_class
            if decoded_item.stats.rarity is not None and len(data) >= 10:
                data[9] = decoded_item.stats.rarity

        elif decoded_item.item_type == 'd':
            if decoded_item.stats.primary_stat is not None and len(data) >= 6:
                struct.pack_into('<H', data, 4, decoded_item.stats.primary_stat)
            if decoded_item.stats.secondary_stat is not None and len(data) >= 10:
                struct.pack_into('<H', data, 8, decoded_item.stats.secondary_stat)
            if decoded_item.stats.manufacturer is not None and len(data) >= 6:
                data[5] = decoded_item.stats.manufacturer
            if decoded_item.stats.item_class is not None and len(data) >= 7:
                data[6] = decoded_item.stats.item_class

        prefix = f'@Ug{decoded_item.item_type}'
        return bit_pack_encode(bytes(data), prefix)

    except Exception as e:
        print(f"Warning: Failed to encode item serial: {e}")
        return decoded_item.serial

def find_and_decode_serials_in_yaml(yaml_data: dict) -> Dict[str, DecodedItem]:
    decoded_serials = {}

    def search_dict(obj, path=""):
        if isinstance(obj, dict):
            for key, value in obj.items():
                new_path = f"{path}.{key}" if path else key
                if isinstance(value, str) and value.startswith('@Ug'):
                    decoded = decode_item_serial(value)
                    if decoded.confidence != "none":
                        decoded_serials[new_path] = decoded
                elif isinstance(value, (dict, list)):
                    search_dict(value, new_path)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                new_path = f"{path}[{i}]"
                if isinstance(item, str) and item.startswith('@Ug'):
                    decoded = decode_item_serial(item)
                    if decoded.confidence != "none":
                        decoded_serials[new_path] = decoded
                elif isinstance(item, (dict, list)):
                    search_dict(item, new_path)

    search_dict(yaml_data)
    return decoded_serials

def insert_decoded_items_in_yaml(yaml_data: dict, decoded_serials: Dict[str, DecodedItem]) -> dict:
    result = yaml_data.copy()

    result['_DECODED_ITEMS'] = {}

    for path, decoded_item in decoded_serials.items():
        item_info = {
            'original_serial': decoded_item.serial,
            'item_type': decoded_item.item_type,
            'category': decoded_item.item_category,
            'confidence': decoded_item.confidence,
            'stats': {}
        }

        if decoded_item.stats.primary_stat is not None:
            item_info['stats']['primary_stat'] = decoded_item.stats.primary_stat
        if decoded_item.stats.secondary_stat is not None:
            item_info['stats']['secondary_stat'] = decoded_item.stats.secondary_stat
        if decoded_item.stats.level is not None:
            item_info['stats']['level'] = decoded_item.stats.level
        if decoded_item.stats.rarity is not None:
            item_info['stats']['rarity'] = decoded_item.stats.rarity
        if decoded_item.stats.manufacturer is not None:
            item_info['stats']['manufacturer'] = decoded_item.stats.manufacturer
        if decoded_item.stats.item_class is not None:
            item_info['stats']['item_class'] = decoded_item.stats.item_class

        result['_DECODED_ITEMS'][path] = item_info

    return result

def extract_and_encode_serials_from_yaml(yaml_data: dict) -> dict:
    result = yaml_data.copy()

    if '_DECODED_ITEMS' not in yaml_data:
        return result

    decoded_items_section = yaml_data['_DECODED_ITEMS']

    for path, item_info in decoded_items_section.items():
        stats = ItemStats()
        if 'stats' in item_info:
            stats_data = item_info['stats']
            stats.primary_stat = stats_data.get('primary_stat')
            stats.secondary_stat = stats_data.get('secondary_stat')
            stats.level = stats_data.get('level')
            stats.rarity = stats_data.get('rarity')
            stats.manufacturer = stats_data.get('manufacturer')
            stats.item_class = stats_data.get('item_class')

        decoded_item = DecodedItem(
            serial=item_info['original_serial'],
            item_type=item_info['item_type'],
            item_category=item_info['category'],
            length=0,
            stats=stats,
            raw_fields={},
            confidence=item_info['confidence']
        )

        new_serial = encode_item_serial(decoded_item)

        set_nested_value(result, path, new_serial)

    if '_DECODED_ITEMS' in result:
        del result['_DECODED_ITEMS']

    return result

def set_nested_value(data: dict, path: str, value: str):
    parts = path.split('.')
    current = data

    for part in parts[:-1]:
        if '[' in part and ']' in part:
            key, index_str = part.split('[')
            index = int(index_str.rstrip(']'))
            current = current[key][index]
        else:
            current = current[part]

    final_part = parts[-1]
    if '[' in final_part and ']' in final_part:
        key, index_str = final_part.split('[')
        index = int(index_str.rstrip(']'))
        current[key][index] = value
    else:
        current[final_part] = value

def derive_key(steamid: str) -> bytes:
    sid = int("".join(ch for ch in steamid if ch.isdigit()), 10)
    sid_le = sid.to_bytes(8, "little", signed=False)
    k = bytearray(BASE_KEY)
    for i in range(8):
        k[i] ^= sid_le[i]
    return bytes(k)

def decrypt_sav_to_yaml(sav_path: Path, steamid: str) -> bytes:
    ciph = sav_path.read_bytes()
    if len(ciph) % 16 != 0:
        raise ValueError(f"input .sav size {len(ciph)} not multiple of 16")
    key = derive_key(steamid)
    pt_padded = AES.new(key, AES.MODE_ECB).decrypt(ciph)

    try:
        body = unpad(pt_padded, 16, style="pkcs7")
    except ValueError:
        body = pt_padded

    yaml_data = zlib.decompress(body)
    return yaml_data

def encrypt_yaml_to_sav(yaml_path: Path, steamid: str) -> bytes:
    current_yaml = yaml_path.read_bytes()
    comp = zlib.compress(current_yaml, level=9)
    adler32 = zlib.adler32(current_yaml) & 0xffffffff
    uncompressed_length = len(current_yaml)
    packed = comp + struct.pack('<I', adler32) + struct.pack('<I', uncompressed_length)

    pt_padded = pad(packed, 16, style="pkcs7")
    key = derive_key(steamid)
    ciph = AES.new(key, AES.MODE_ECB).encrypt(pt_padded)
    return ciph

def main():
    parser = argparse.ArgumentParser(
        prog="blcrypt",
        description=(
            "Encrypt/decrypt BL4 saves - decrypt to readable YAML, edit values, then encrypt.\n"
            "I'm not responsible for any damage you do your save file. Backup your save file before using this, and be smart."
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )

    sub = parser.add_subparsers(dest="cmd", required=True)

    p_dec = sub.add_parser(
        "decrypt",
        help="Decrypt a .sav to readable YAML.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    p_dec.add_argument("-in", "--input", required=True, help="Path to input .sav")
    p_dec.add_argument("-out", "--output", help="Path to output .yaml (default: <input>.yaml)")
    p_dec.add_argument("-id", "--steamid", required=True, help="SteamID (e.g., 7656119...)")
    p_dec.add_argument("--decode-serials", action="store_true",
                      help="Decode item serials and add editable stats section to YAML")
    p_dec.epilog = (
        "Examples:\n"
        "  blcrypt decrypt -in 1.sav -out save.yaml -id 7656119XXXXXXXXX\n"
        "  blcrypt decrypt -in 1.sav -out save.yaml -id 7656119XXXXXXXXX --decode-serials\n"
        "If PKCS7 or zlib errors appear, verify the SteamID is correct.\n"
        "Use --decode-serials to decode item stats for editing."
    )

    p_enc = sub.add_parser(
        "encrypt",
        help="Encrypt a YAML to .sav to be read by the game.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    p_enc.add_argument("-in", "--input", required=True, help="Path to input .yaml")
    p_enc.add_argument("-out", "--output", help="Path to output .sav (default: <input>.sav)")
    p_enc.add_argument("-id", "--steamid", required=True, help="Steam ID (17 digits, starts with 7656119...)")
    p_enc.add_argument("--encode-serials", action="store_true",
                      help="Encode modified item stats back to serials before encrypting")
    p_enc.epilog = (
        "Examples:\n"
        "  blcrypt encrypt -in save.yaml -out 1.sav -id 7656119XXXXXXXXX\n"
        "  blcrypt encrypt -in save.yaml -out 1.sav -id 7656119XXXXXXXXX --encode-serials\n"
        "The game should accept the .sav if the Steam ID matches the save owner.\n"
        "Use --encode-serials if you edited item stats and need them re-encoded."
    )

    args = parser.parse_args()

    try:
        if args.cmd == "decrypt":
            in_path = Path(args.input)
            out_path = Path(args.output) if args.output else in_path.with_suffix(".yaml")
            yaml_bytes = decrypt_sav_to_yaml(in_path, args.steamid)

            if args.decode_serials:
                yaml_data = yaml.safe_load(yaml_bytes.decode('utf-8'))
                decoded_serials = find_and_decode_serials_in_yaml(yaml_data)

                if decoded_serials:
                    yaml_data_with_decoded = insert_decoded_items_in_yaml(yaml_data, decoded_serials)
                    yaml_output = yaml.dump(yaml_data_with_decoded, default_flow_style=False, allow_unicode=True)
                    out_path.write_text(yaml_output, encoding='utf-8')
                    print(f"wrote {out_path} with {len(decoded_serials)} decoded item serials")
                    print("Edit the '_DECODED_ITEMS' section to modify item stats, then encrypt with --encode-serials")
                else:
                    yaml_output = yaml.dump(yaml_data, default_flow_style=False, allow_unicode=True)
                    out_path.write_text(yaml_output, encoding='utf-8')
                    print(f"wrote {out_path} (no item serials found to decode)")
            else:
                out_path.write_bytes(yaml_bytes)
                print(f"wrote {out_path}")

        elif args.cmd == "encrypt":
            in_path = Path(args.input)
            out_path = Path(args.output) if args.output else in_path.with_suffix(".sav")

            if args.encode_serials:
                yaml_content = in_path.read_text(encoding='utf-8')
                yaml_data = yaml.safe_load(yaml_content)

                if '_DECODED_ITEMS' in yaml_data:
                    yaml_data_with_encoded = extract_and_encode_serials_from_yaml(yaml_data)
                    yaml_output = yaml.dump(yaml_data_with_encoded, default_flow_style=False, allow_unicode=True)

                    temp_yaml = in_path.with_suffix('.temp.yaml')
                    temp_yaml.write_text(yaml_output, encoding='utf-8')
                    sav_bytes = encrypt_yaml_to_sav(temp_yaml, args.steamid)
                    temp_yaml.unlink()

                    out_path.write_bytes(sav_bytes)
                    print(f"wrote {out_path} with re-encoded item serials")
                else:
                    sav_bytes = encrypt_yaml_to_sav(in_path, args.steamid)
                    out_path.write_bytes(sav_bytes)
                    print(f"wrote {out_path} (no decoded items section found)")
            else:
                sav_bytes = encrypt_yaml_to_sav(in_path, args.steamid)
                out_path.write_bytes(sav_bytes)
                print(f"wrote {out_path}")

        else:
            parser.error("unknown command")
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
