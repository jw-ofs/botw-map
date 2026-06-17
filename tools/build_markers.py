#!/usr/bin/env python3
"""Parse the datamined Breath of the Wild dataset (botw-unexplored Data.cpp) and
emit markers.js for the interactive map.

Coordinates in Data.cpp are game-world units (x = world X, y = world Z).
Projection onto the 24000x20000 objmap tile image (derived from objmap's CRS):
    px = 2*x + 12000      py = 2*y + 10000
The frontend places each marker via xy(px,py) = L.latLng(-py/128, px/128).
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "_cache", "Data.cpp")
OUT = os.path.join(ROOT, "markers.js")

NUM = r"(-?\d+(?:\.\d+)?)"   # float/int, optional trailing 'f' consumed separately
F = r"f?"


def proj(x, y):
    return round(2 * x + 12000, 1), round(2 * y + 10000, 1)


def main():
    t = open(SRC, encoding="utf-8", errors="replace").read()
    markers = []

    # ---- Koroks: Korok(hash, "internalName", x, y, zeldaId) ----
    korok_re = re.compile(
        r'\bKorok\(\s*(\d+)\s*,\s*"([^"]*)"\s*,\s*' + NUM + F + r'\s*,\s*' + NUM + F + r'\s*,\s*(\d+)\s*\)')
    # ---- Korok hint table: { id, { "text", "image" } } ----
    info_re = re.compile(
        r'\{\s*(\d+)\s*,\s*\{\s*"((?:\\.|[^"\\])*)"\s*,\s*"([^"]*)"\s*\}\s*\}')
    infos = {int(m.group(1)): m.group(2) for m in info_re.finditer(t)}

    koroks = korok_re.findall(t)
    for hsh, iname, x, y, zid in koroks:
        px, py = proj(float(x), float(y))
        hint = infos.get(int(zid), "")
        markers.append(dict(id=f"k{hsh}", cat="korok", name="Korok Seed", px=px, py=py, desc=hint))

    # ---- Shrines: Shrine(hash, "name", x, y)  (exclude DLCShrine) ----
    shrine_re = re.compile(
        r'(?<!DLC)\bShrine\(\s*(\d+)\s*,\s*"([^"]*)"\s*,\s*' + NUM + F + r'\s*,\s*' + NUM + F + r'\s*\)')
    for hsh, name, x, y in shrine_re.findall(t):
        px, py = proj(float(x), float(y))
        markers.append(dict(id=f"s{hsh}", cat="shrine", name=name, px=px, py=py, desc="Sheikah Shrine"))

    # ---- DLC Shrines: DLCShrine(hash, x, y) (no name) ----
    dlc_re = re.compile(r'\bDLCShrine\(\s*(\d+)\s*,\s*' + NUM + F + r'\s*,\s*' + NUM + F + r'\s*\)')
    for i, (hsh, x, y) in enumerate(dlc_re.findall(t), 1):
        px, py = proj(float(x), float(y))
        markers.append(dict(id=f"d{hsh}", cat="dlcshrine", name=f"EX Shrine {i}", px=px, py=py,
                            desc="The Champions' Ballad (DLC)"))

    # ---- Enemies: Hinox / Talus / Molduga (hash, x, y) ----
    for struct, cat, label in (("Hinox", "hinox", "Hinox"),
                               ("Talus", "talus", "Stone Talus"),
                               ("Molduga", "molduga", "Molduga")):
        rx = re.compile(r'\b' + struct + r'\(\s*(\d+)\s*,\s*' + NUM + F + r'\s*,\s*' + NUM + F + r'\s*\)')
        for hsh, x, y in rx.findall(t):
            px, py = proj(float(x), float(y))
            markers.append(dict(id=f"{cat[0]}{hsh}", cat=cat, name=label, px=px, py=py, desc=""))

    # ---- Locations: Location(hash, "name", x, y) -> bucket by name ----
    loc_re = re.compile(
        r'\bLocation\(\s*(\d+)\s*,\s*"([^"]*)"\s*,\s*' + NUM + F + r'\s*,\s*' + NUM + F + r'\s*\)')
    TOWNS = {"Korok Forest", "Gerudo Town", "Goron City", "Rito Village", "Zora's Domain",
             "Kakariko Village", "Hateno Village", "Lurelin Village", "Tarrey Town"}
    for hsh, name, x, y in loc_re.findall(t):
        if name.startswith("UMii"):
            continue  # internal untranslated shop names
        px, py = proj(float(x), float(y))
        if name.endswith(" Tower"):
            cat, desc = "tower", "Sheikah Tower"
        elif name == "Great Fairy Fountain":
            cat, desc = "fairy", "Great Fairy Fountain"
        elif name.startswith("Divine Beast"):
            cat, desc = "divinebeast", "Divine Beast"
        elif name.endswith(" Stable"):
            cat, desc = "stable", "Stable"
        elif "Tech Lab" in name:
            cat, desc = "lab", "Ancient Tech Lab"
        elif name in TOWNS or name.endswith((" Village", " Town", " City", " Domain")):
            cat, desc = "town", "Town / Settlement"
        else:
            cat, desc = "region", ""
        markers.append(dict(id=f"l{hsh}", cat=cat, name=name, px=px, py=py, desc=desc))

    # ---- Memories (curated, if present) ----
    mem_path = os.path.join(ROOT, "_cache", "memories.json")
    if os.path.exists(mem_path):
        for m in json.load(open(mem_path, encoding="utf-8")):
            px, py = proj(m["x"], m["y"])
            markers.append(dict(id=f"mem{m['n']}", cat="memory",
                                name=f"{m['n']}. {m['name']}", px=px, py=py, desc=m.get("desc", "")))

    # ---- Categories (sidebar groups + icons/colors) ----
    categories = [
        dict(group="Progress", id="shrine", name="Shrines", icon="⛩️", color="#e8943c"),
        dict(group="Progress", id="dlcshrine", name="EX / DLC Shrines", icon="⛩️", color="#c062d0"),
        dict(group="Progress", id="tower", name="Sheikah Towers", icon="\U0001f5fc", color="#5ad1e6"),
        dict(group="Progress", id="divinebeast", name="Divine Beasts", icon="\U0001f409", color="#d14e8c"),
        dict(group="Collectibles", id="korok", name="Korok Seeds", icon="\U0001f343", color="#6fc24f"),
        dict(group="Enemies", id="hinox", name="Hinox", icon="\U0001f479", color="#c0504d"),
        dict(group="Enemies", id="talus", name="Stone Talus", icon="\U0001faa8", color="#9a959a"),
        dict(group="Enemies", id="molduga", name="Molduga", icon="\U0001f988", color="#d9a441"),
        dict(group="Places", id="town", name="Towns & Villages", icon="\U0001f3d8️", color="#5b9bd5"),
        dict(group="Places", id="stable", name="Stables", icon="\U0001f434", color="#b07a4a"),
        dict(group="Places", id="fairy", name="Great Fairy Fountains", icon="\U0001f9da", color="#ff7fd0"),
        dict(group="Places", id="lab", name="Ancient Tech Labs", icon="\U0001f52c", color="#3d9970"),
        dict(group="Story", id="memory", name="Captured Memories", icon="\U0001f4ad", color="#f0e3c4"),
        dict(group="Reference", id="region", name="Location Labels", icon="\U0001f4cd", color="#7c879b"),
    ]

    # ---- counts report ----
    from collections import Counter
    cnt = Counter(m["cat"] for m in markers)
    print("Markers by category:")
    for c in categories:
        print(f"  {c['id']:12} {cnt.get(c['id'], 0)}")
    print(f"  {'TOTAL':12} {len(markers)}")

    # ---- sanity: a couple known points ----
    known = {m["name"]: (m["px"], m["py"]) for m in markers if m["name"] in
             ("Bosh Kala Shrine", "Hawa Koth Shrine", "Great Plateau Tower")}
    print("Sanity (expect Bosh Kala ~ center-south, Hawa Koth ~ SW):")
    for k, v in known.items():
        print(f"  {k}: px={v[0]} py={v[1]}")

    # ---- write markers.js ----
    lines = ["/* AUTO-GENERATED by tools/build_markers.py — datamined BotW markers.",
             "   Source: lud99/botw-unexplored Data.cpp (game-world coords).",
             "   px,py = pixel on the 24000x20000 objmap tile image: px=2x+12000, py=2y+10000. */",
             "", "const CATEGORIES = ["]
    for c in categories:
        lines.append("  " + json.dumps(c, ensure_ascii=False) + ",")
    lines.append("];")
    lines.append("")
    lines.append("const MARKERS = [")
    for m in markers:
        lines.append("  " + json.dumps(m, ensure_ascii=False) + ",")
    lines.append("];")
    open(OUT, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print(f"\nWrote {OUT} ({os.path.getsize(OUT)/1024:.0f} KB, {len(markers)} markers)")


if __name__ == "__main__":
    main()
