"""JSON <-> VPC converter — shared module for CLI and web app."""
import json
import re


def make_abbreviation(text: str) -> str:
    words = text.split()
    return ''.join(w[0].upper() for w in words if w)


def serialize_vpc(obj) -> str:
    if obj is None:
        return 'null'
    if isinstance(obj, bool):
        return 'true' if obj else 'false'
    if isinstance(obj, (int, float)):
        return json.dumps(obj)
    if isinstance(obj, str):
        return json.dumps(obj, ensure_ascii=False)
    if isinstance(obj, list):
        if not obj:
            return '[]'
        items = [serialize_vpc(item) for item in obj]
        return '[' + ','.join(items) + ']'
    if isinstance(obj, dict):
        if not obj:
            return '{}'
        parts = [f'{key}:{serialize_vpc(value)}' for key, value in obj.items()]
        return '{' + ','.join(parts) + '}'
    return json.dumps(obj, ensure_ascii=False)


def json_to_vpc(data: dict) -> str:
    if 'Abbreviation' not in data and 'Text' in data:
        data = dict(data)
        data['Abbreviation'] = make_abbreviation(data['Text'])
    return serialize_vpc(data)


def fix_vpc(text):
    """Wrap bare VPC keys in quotes and escape raw control chars inside strings.

    Real-world VPC files (e.g. choir lyric exports) embed literal newlines,
    tabs and carriage returns inside quoted string values, which is invalid
    JSON ("Invalid control character"). This pass quotes bare keys AND escapes
    raw control characters found inside string values so the result parses.
    """
    # Strip UTF-8 BOM if present (also handled via utf-8-sig decoding upstream)
    if text.startswith('\ufeff'):
        text = text.lstrip('\ufeff')
    result = []
    in_string = False
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == '"':
            in_string = not in_string
            result.append(c)
            i += 1
            continue
        if c == '\\' and in_string:
            result.append(c)
            i += 1
            if i < n:
                result.append(text[i])
                i += 1
            continue
        if in_string:
            o = ord(c)
            if c == '\n':
                result.append('\\n')
            elif c == '\r':
                # Normalize CRLF/CR to \n escape; avoid doubling on \r\n
                if i + 1 < n and text[i + 1] == '\n':
                    i += 1
                result.append('\\n')
            elif c == '\t':
                result.append('\\t')
            elif o < 0x20:
                # Strip other raw control chars (0x00-0x1F)
                pass
            else:
                result.append(c)
            i += 1
            continue
        if not in_string and c in '{,':
            result.append(c)
            i += 1
            while i < n and text[i] in ' \t\n\r':
                result.append(text[i])
                i += 1
            start = i
            while i < n and (text[i].isalnum() or text[i] == '_'):
                i += 1
            if i < n and text[i] == ':':
                key = text[start:i]
                if key:
                    result.append('"' + key + '"')
                else:
                    i = start
            else:
                i = start
        else:
            result.append(c)
            i += 1
    return ''.join(result)


def vpc_to_json(text: str) -> dict:
    if isinstance(text, (bytes, bytearray)):
        text = bytes(text).decode('utf-8-sig')
    if text.startswith('\ufeff'):
        text = text.lstrip('\ufeff')
    fixed = fix_vpc(text)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        # Lenient fallback for any residual raw control chars
        return json.loads(fixed, strict=False)
