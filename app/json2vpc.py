"""JSON ↔ VPC converter — shared module for CLI and web app."""
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
    """Wrap bare VPC keys in quotes so the text becomes valid JSON."""
    result = []
    in_string = False
    i = 0
    while i < len(text):
        c = text[i]
        if c == '"':
            in_string = not in_string
            result.append(c)
            i += 1
            continue
        if c == '\\' and in_string:
            result.append(c)
            i += 1
            if i < len(text):
                result.append(text[i])
                i += 1
            continue
        if not in_string and c in '{,':
            result.append(c)
            i += 1
            while i < len(text) and text[i] in ' \t\n\r':
                result.append(text[i])
                i += 1
            start = i
            while i < len(text) and (text[i].isalnum() or text[i] == '_'):
                i += 1
            if i < len(text) and text[i] == ':':
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
    fixed = fix_vpc(text)
    return json.loads(fixed)
