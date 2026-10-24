"""Helpers for the construction_* translation files (.pot / .po).

  python scripts/i18n_tools.py list                      unique source strings, one per line (JSON)
  python scripts/i18n_tools.py apply <lang> <json file>  fill addons/construction_*/i18n/<lang>.po
                                                         from a {"English": "Translation"} mapping
  python scripts/i18n_tools.py missing <lang> <json>     strings still untranslated for a language
"""
import glob
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "addons")


def unquote(line):
    line = line.strip()
    assert line.startswith('"') and line.endswith('"'), line
    return json.loads(line)  # PO string syntax is JSON-compatible for our content


def quote(text):
    return json.dumps(text, ensure_ascii=False)


def parse(path):
    """Return a list of entries: dict(raw_lines=[...], msgid=str, start, end)."""
    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")
    entries, i = [], 0
    while i < len(lines):
        if lines[i].startswith("msgid "):
            start = i
            msgid = unquote(lines[i][6:])
            i += 1
            while i < len(lines) and lines[i].startswith('"'):
                msgid += unquote(lines[i])
                i += 1
            assert lines[i].startswith("msgstr "), (path, i)
            str_start = i
            i += 1
            while i < len(lines) and lines[i].startswith('"'):
                i += 1
            entries.append({"msgid": msgid, "id_start": start, "str_start": str_start, "str_end": i})
        else:
            i += 1
    return lines, entries


def source_strings():
    seen = {}
    for pot in sorted(glob.glob(os.path.join(ROOT, "construction_*", "i18n", "*.pot"))):
        _, entries = parse(pot)
        for e in entries:
            if e["msgid"]:
                seen.setdefault(e["msgid"], os.path.basename(os.path.dirname(os.path.dirname(pot))))
    return seen


def apply(lang, mapping):
    total = filled = 0
    for po in sorted(glob.glob(os.path.join(ROOT, "construction_*", "i18n", f"{lang}.po"))):
        lines, entries = parse(po)
        out, cursor = [], 0
        for e in entries:
            if not e["msgid"]:
                continue
            total += 1
            translation = mapping.get(e["msgid"])
            if translation is None:
                continue
            filled += 1
            out.extend(lines[cursor:e["str_start"]])
            out.append(f"msgstr {quote(translation)}")
            cursor = e["str_end"]
        out.extend(lines[cursor:])
        with open(po, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(out))
    return total, filled


def missing(lang, mapping):
    return [s for s in source_strings() if s not in mapping]


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "list":
        print(json.dumps(list(source_strings()), ensure_ascii=False, indent=0))
    elif cmd in ("apply", "missing") and len(sys.argv) == 4:
        with open(sys.argv[3], encoding="utf-8") as f:
            mapping = json.load(f)
        if cmd == "apply":
            total, filled = apply(sys.argv[2], mapping)
            print(f"{sys.argv[2]}: filled {filled} of {total} entries")
        else:
            print(json.dumps(missing(sys.argv[2], mapping), ensure_ascii=False, indent=0))
    else:
        sys.exit(__doc__)
