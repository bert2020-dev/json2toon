#!/usr/bin/env python3
"""
json2toon - Convert between JSON and TOON (Token-Optimized Object Notation).

Input format is auto-detected from content; a .json/.toon extension, if
present, is used only as a hint. Reads from a file or stdin ('-').

Usage:
    json2toon.py some_file.json            # -> some_file.toon
    json2toon.py some_file.toon            # -> some_file.json
    json2toon.py some_file.json out.toon   # explicit output name
    json2toon.py some_file.json -          # write to stdout
    json2toon.py - < in.json               # stdin -> stdout
    json2toon.py some_file.json -f         # overwrite without prompting
"""

import argparse
import json
import os
import re
import sys


_ARRAY_KEY_RE = re.compile(r'^(.+?)\[(\d+)\](?:\{([^}]*)\})?$')
_ANON_ARRAY_RE = re.compile(r'^\[(\d+)\](?:\{([^}]*)\})?:\s*(.*)$')
_SPECIAL_CHARS = set(':,[]{}#"\'\n\r\t\\')


# --------------------------------------------------------------------- encode

def _encode_string(s):
    if s == '':
        return '""'
    if s != s.strip():
        return json.dumps(s)
    if any(c in _SPECIAL_CHARS for c in s):
        return json.dumps(s)
    if s.lower() in ('null', 'true', 'false'):
        return json.dumps(s)
    if s.startswith('-'):
        return json.dumps(s)
    try:
        float(s)
        return json.dumps(s)
    except ValueError:
        pass
    return s


def _encode_primitive(v):
    if v is None:
        return 'null'
    if v is True:
        return 'true'
    if v is False:
        return 'false'
    if isinstance(v, (int, float)):
        return json.dumps(v)
    if isinstance(v, str):
        return _encode_string(v)
    raise TypeError(f'Cannot encode type {type(v).__name__}')


def _is_uniform_objects(arr):
    if not arr or not all(isinstance(x, dict) and x for x in arr):
        return False
    keys = set(arr[0].keys())
    return all(set(x.keys()) == keys for x in arr)


def _all_values_primitive(arr):
    return all(not isinstance(v, (dict, list)) for x in arr for v in x.values())


def _encode_array_field(key_str, arr, indent):
    pad = '  ' * indent
    if not arr:
        return [f'{pad}{key_str}[0]:']
    if _is_uniform_objects(arr) and _all_values_primitive(arr):
        fields = list(arr[0].keys())
        header = f'{pad}{key_str}[{len(arr)}]{{{",".join(fields)}}}:'
        row_pad = '  ' * (indent + 1)
        lines = [header]
        for row in arr:
            lines.append(row_pad + ','.join(_encode_primitive(row[f]) for f in fields))
        return lines
    if all(not isinstance(x, (dict, list)) for x in arr):
        vals = ','.join(_encode_primitive(x) for x in arr)
        return [f'{pad}{key_str}[{len(arr)}]: {vals}']
    lines = [f'{pad}{key_str}[{len(arr)}]:']
    for item in arr:
        lines.extend(_encode_list_item(item, indent + 1))
    return lines


def _encode_list_item(item, indent):
    pad = '  ' * indent
    if isinstance(item, dict):
        if not item:
            return [f'{pad}-']
        keys = list(item.keys())
        first_lines = _encode_kv(keys[0], item[keys[0]], 0)
        out = [f'{pad}- {first_lines[0]}']
        cont_pad = pad + '  '
        for ln in first_lines[1:]:
            out.append(cont_pad + ln)
        for k in keys[1:]:
            out.extend(_encode_kv(k, item[k], indent + 1))
        return out
    if isinstance(item, list):
        if not item:
            return [f'{pad}- [0]:']
        if all(not isinstance(x, (dict, list)) for x in item):
            return [f'{pad}- [{len(item)}]: ' + ','.join(_encode_primitive(x) for x in item)]
        out = [f'{pad}- [{len(item)}]:']
        for sub in item:
            out.extend(_encode_list_item(sub, indent + 1))
        return out
    return [f'{pad}- {_encode_primitive(item)}']


def _encode_kv(key, value, indent):
    pad = '  ' * indent
    k = _encode_string(key) if isinstance(key, str) else str(key)
    if isinstance(value, dict):
        if not value:
            return [f'{pad}{k}:']
        lines = [f'{pad}{k}:']
        for kk, vv in value.items():
            lines.extend(_encode_kv(kk, vv, indent + 1))
        return lines
    if isinstance(value, list):
        return _encode_array_field(k, value, indent)
    return [f'{pad}{k}: {_encode_primitive(value)}']


def encode_toon(value):
    if isinstance(value, dict):
        if not value:
            return ''
        lines = []
        for k, v in value.items():
            lines.extend(_encode_kv(k, v, 0))
        return '\n'.join(lines) + '\n'
    if isinstance(value, list):
        if not value:
            return ''
        lines = _encode_array_field('', value, 0)
        return '\n'.join(lines) + '\n'
    return _encode_primitive(value) + '\n'


# --------------------------------------------------------------------- decode

def _split_kv(s):
    in_str = False
    qc = None
    depth = 0
    i = 0
    while i < len(s):
        c = s[i]
        if in_str:
            if c == '\\' and qc == '"':
                i += 2
                continue
            if c == qc:
                in_str = False
        elif c in ('"', "'"):
            in_str = True
            qc = c
        elif c in '[{':
            depth += 1
        elif c in ']}':
            depth -= 1
        elif c == ':' and depth == 0:
            return s[:i], s[i + 1:].lstrip()
        i += 1
    return s, None


def _split_csv(s):
    if s == '':
        return []
    parts, buf = [], []
    depth = 0
    in_str = False
    qc = None
    i = 0
    while i < len(s):
        c = s[i]
        if in_str:
            buf.append(c)
            if c == '\\' and qc == '"' and i + 1 < len(s):
                buf.append(s[i + 1])
                i += 2
                continue
            if c == qc:
                in_str = False
        elif c in ('"', "'"):
            in_str = True
            qc = c
            buf.append(c)
        elif c in '[{':
            depth += 1
            buf.append(c)
        elif c in ']}':
            depth -= 1
            buf.append(c)
        elif c == ',' and depth == 0:
            parts.append(''.join(buf))
            buf = []
        else:
            buf.append(c)
        i += 1
    parts.append(''.join(buf))
    return parts


def _unquote(s):
    s = s.strip()
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            return s[1:-1]
    if len(s) >= 2 and s[0] == "'" and s[-1] == "'":
        return s[1:-1]
    return s


def _parse_scalar(s):
    s = s.strip()
    if s == '' or s == 'null':
        return None
    if s == 'true':
        return True
    if s == 'false':
        return False
    if s[0] in ('"', "'"):
        return _unquote(s)
    try:
        if any(c in s for c in '.eE') and s not in ('-', '+'):
            return float(s)
        return int(s)
    except ValueError:
        pass
    return s


def _parse_key(s):
    return _unquote(s.strip())


def _parse_array_body(lines, i, header_indent, count, fields):
    if fields is not None:
        arr = []
        while i < len(lines) and lines[i][0] > header_indent:
            cells = _split_csv(lines[i][1])
            if len(cells) != len(fields):
                raise ValueError(
                    f'row has {len(cells)} cells, expected {len(fields)}: '
                    f'{lines[i][1]!r}'
                )
            arr.append({f: _parse_scalar(c) for f, c in zip(fields, cells)})
            i += 1
        return arr, i
    if i < len(lines) and lines[i][0] > header_indent:
        return _parse_list(lines, i, lines[i][0])
    return [], i


def _parse_list(lines, i, indent):
    items = []
    while i < len(lines):
        li, content = lines[i]
        if li != indent:
            break
        if not (content.startswith('- ') or content == '-'):
            break
        stripped = content[2:] if content.startswith('- ') else ''
        item_indent = indent + 2
        item_lines = [(item_indent, stripped)]
        i += 1
        while i < len(lines) and lines[i][0] > indent:
            item_lines.append(lines[i])
            i += 1
        if stripped == '':
            if len(item_lines) > 1:
                sub, _ = _parse_block(item_lines, 1, item_lines[1][0])
                items.append(sub)
            else:
                items.append(None)
            continue
        m = _ANON_ARRAY_RE.match(stripped)
        if m:
            count = int(m.group(1))
            fields_raw = m.group(2)
            inline = m.group(3)
            fields = [f.strip() for f in fields_raw.split(',')] if fields_raw else None
            if inline.strip():
                items.append([_parse_scalar(v) for v in _split_csv(inline)])
            else:
                body, _ = _parse_array_body(item_lines, 1, item_indent, count, fields)
                items.append(body)
            continue
        item, _ = _parse_block(item_lines, 0, item_indent)
        items.append(item)
    return items, i


def _parse_object(lines, i, indent):
    result = {}
    while i < len(lines):
        li, content = lines[i]
        if li != indent:
            break
        key_part, rest = _split_kv(content)
        if rest is None:
            break
        m = None
        if key_part and key_part[0] not in ('"', "'"):
            m = _ARRAY_KEY_RE.match(key_part)
        if m:
            key = _parse_key(m.group(1))
            count = int(m.group(2))
            fields_raw = m.group(3)
            fields = [f.strip() for f in fields_raw.split(',')] if fields_raw is not None else None
            if rest.strip() == '':
                arr, i = _parse_array_body(lines, i + 1, indent, count, fields)
                result[key] = arr
            else:
                result[key] = [_parse_scalar(v) for v in _split_csv(rest)]
                i += 1
        elif rest.strip() == '':
            if i + 1 < len(lines) and lines[i + 1][0] > indent:
                val, i = _parse_block(lines, i + 1, lines[i + 1][0])
                result[_parse_key(key_part)] = val
            else:
                result[_parse_key(key_part)] = {}
                i += 1
        else:
            result[_parse_key(key_part)] = _parse_scalar(rest)
            i += 1
    return result, i


def _parse_block(lines, i, indent):
    if i >= len(lines):
        return None, i
    _, content = lines[i]
    if content.startswith('- ') or content == '-':
        return _parse_list(lines, i, indent)
    m = _ANON_ARRAY_RE.match(content)
    if m:
        count = int(m.group(1))
        fields_raw = m.group(2)
        inline = m.group(3)
        fields = [f.strip() for f in fields_raw.split(',')] if fields_raw else None
        if inline.strip():
            return [_parse_scalar(v) for v in _split_csv(inline)], i + 1
        return _parse_array_body(lines, i + 1, indent, count, fields)
    key_part, rest = _split_kv(content)
    if rest is None:
        return _parse_scalar(content), i + 1
    return _parse_object(lines, i, indent)


def decode_toon(text):
    lines = []
    for raw in text.splitlines():
        if not raw.strip():
            continue
        stripped = raw.lstrip(' ')
        if stripped.startswith('#'):
            continue
        indent = len(raw) - len(stripped)
        lines.append((indent, raw.strip()))

    if not lines:
        return {}

    first = lines[0][1]
    if first.startswith('- ') or first == '-':
        result, i = _parse_list(lines, 0, 0)
    else:
        m = _ANON_ARRAY_RE.match(first)
        if m:
            count = int(m.group(1))
            fields_raw = m.group(2)
            inline = m.group(3)
            fields = [f.strip() for f in fields_raw.split(',')] if fields_raw else None
            if inline.strip():
                result, i = [_parse_scalar(v) for v in _split_csv(inline)], 1
            else:
                result, i = _parse_array_body(lines, 1, 0, count, fields)
        else:
            key_part, rest = _split_kv(first)
            if rest is None:
                if len(lines) > 1:
                    raise ValueError(
                        f'unexpected content at line 2: {lines[1][1]!r}'
                    )
                return _parse_scalar(first)
            result, i = _parse_object(lines, 0, 0)

    if i < len(lines):
        raise ValueError(
            f'unexpected content at line {i + 1}: {lines[i][1]!r}'
        )
    return result


# --------------------------------------------------------------- detection

def _detect_kind(path, text):
    """
    Detect input format ('json' or 'toon').

    Content is authoritative: if the text parses as JSON we call it JSON.
    Otherwise we call it TOON, unless the file's extension claims JSON — in
    which case we still return 'json' so the caller can surface a proper
    JSON syntax error instead of trying to parse broken JSON as TOON.
    """
    if not text.strip():
        raise ValueError('input is empty')

    stripped = text.lstrip()
    if stripped.startswith('#'):
        # TOON comment lines; JSON has no comment syntax.
        return 'toon'

    try:
        json.loads(text)
        return 'json'
    except json.JSONDecodeError:
        pass

    ext = ''
    if path and path != '-':
        ext = os.path.splitext(path)[1].lower()
    if ext == '.json':
        return 'json'
    return 'toon'


# ------------------------------------------------------------------------ cli

def main(argv=None):
    parser = argparse.ArgumentParser(
        prog='json2toon',
        description='Convert between JSON and TOON (Token-Optimized Object '
                    'Notation). Input format is auto-detected from content; '
                    'a .json/.toon extension, if present, is used only as a '
                    'hint.',
    )
    parser.add_argument(
        'input', nargs='?', default='-',
        help='Input file (.json or .toon), or "-" for stdin (default).',
    )
    parser.add_argument(
        'output', nargs='?', default=None,
        help='Output file. Defaults to input with swapped extension, or '
             'stdout when reading from stdin. Use "-" for stdout.',
    )
    parser.add_argument(
        '-f', '--force', action='store_true',
        help='Overwrite the output file without prompting.',
    )
    args = parser.parse_args(argv)

    in_path = args.input

    # -------- read input --------
    if in_path == '-':
        try:
            text = sys.stdin.read()
        except OSError as e:
            print(f'json2toon: error: reading stdin: {e}', file=sys.stderr)
            return 1
        source_name = '<stdin>'
        base = None
    else:
        if not os.path.exists(in_path):
            print(f'json2toon: error: {in_path}: no such file', file=sys.stderr)
            return 1
        try:
            with open(in_path, 'r', encoding='utf-8') as f:
                text = f.read()
        except OSError as e:
            print(f'json2toon: error: {in_path}: {e}', file=sys.stderr)
            return 1
        source_name = in_path
        base = os.path.splitext(in_path)[0]

    # -------- detect + convert --------
    try:
        kind = _detect_kind(in_path, text)
        if kind == 'json':
            data = json.loads(text)
            out = encode_toon(data)
            default_out = (base + '.toon') if base else '-'
        else:
            data = decode_toon(text)
            out = json.dumps(data, indent=2, ensure_ascii=False)
            default_out = (base + '.json') if base else '-'
    except json.JSONDecodeError as e:
        print(f'json2toon: error: {source_name}: invalid JSON: {e}',
              file=sys.stderr)
        return 2
    except ValueError as e:
        # Raised by _detect_kind (empty input) or decode_toon (bad TOON).
        print(f'json2toon: error: {source_name}: {e}', file=sys.stderr)
        return 2
    except TypeError as e:
        print(f'json2toon: error: {source_name}: {e}', file=sys.stderr)
        return 2

    if not out.endswith('\n'):
        out += '\n'

    out_path = args.output if args.output is not None else default_out

    # -------- write output --------
    if out_path == '-':
        sys.stdout.write(out)
        return 0

    if os.path.exists(out_path) and not args.force:
        try:
            reply = input(f'{out_path} exists. Overwrite? [y/N] ').strip().lower()
        except EOFError:
            reply = ''
        if reply not in ('y', 'yes'):
            print('json2toon: aborted', file=sys.stderr)
            return 1

    try:
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(out)
    except OSError as e:
        print(f'json2toon: error: {out_path}: {e}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
