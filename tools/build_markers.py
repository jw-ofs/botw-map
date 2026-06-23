#!/usr/bin/env python3
"""Parse the datamined Breath of the Wild dataset (botw-unexplored Data.cpp) and
emit markers.js + quests.js for the interactive map.

Coordinates in Data.cpp are game-world units (x = world X, y = world Z).
Projection onto the 24000x20000 objmap tile image (derived from objmap's CRS):
    px = 2*x + 12000      py = 2*y + 10000
The frontend places each marker via xy(px,py) = L.latLng(-py/128, px/128).
"""
import json
import math
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "_cache", "Data.cpp")
MLOC = os.path.join(ROOT, "_cache", "map_locations.js")
OUT = os.path.join(ROOT, "markers.js")
QOUT = os.path.join(ROOT, "quests.js")

SOURCES = {
    SRC: "https://raw.githubusercontent.com/lud99/botw-unexplored/master/source/Data.cpp",
    MLOC: "https://raw.githubusercontent.com/MrCheeze/botw-object-map/gh-pages/map_locations.js",
}


def ensure(path):
    """Download a source file into _cache/ if it isn't already present."""
    if not os.path.exists(path):
        import urllib.request
        os.makedirs(os.path.dirname(path), exist_ok=True)
        print("downloading", os.path.basename(path), "...")
        urllib.request.urlretrieve(SOURCES[path], path)
    return path


def load_locations():
    """Parse MrCheeze/botw-object-map map_locations.js (var locations = {...};)."""
    raw = open(ensure(MLOC), encoding="utf-8", errors="replace").read()
    return json.loads(raw[raw.index("{"):raw.rindex("}") + 1])

NUM = r"(-?\d+(?:\.\d+)?)"   # float/int, optional trailing 'f' consumed separately
F = r"f?"

# Hyrule Castle interior rooms — all project to ~the same coords and pile into an
# unreadable text stack on the overworld; drop them from the location labels.
CASTLE_ROOMS = {
    "Sanctum", "Observation Room", "First Gatehouse", "Second Gatehouse",
    "East Passage", "West Passage", "Dining Hall", "Guards' Chamber", "Library",
    "Lockup", "Princess Zelda's Room", "Princess Zelda's Study", "King's Study",
    "Docks", "Central Square",
}

# Great Fairies — name the 4 identically-named "Great Fairy Fountain" locations by
# matching to the fairy NPC world coords (Npc_DressFairy_00..03).
GREAT_FAIRIES = [("Cotera", 1976.0, 846.0), ("Mija", 4110.77, -1377.55),
                 ("Kaysa", -3538.73, -746.06), ("Tera", -4870.94, 3825.82)]

# The 13 photo-memory spots (RememberTag), labelled by location and album number,
# ordered by album number. Coords are game-world (x, z); verified against landmarks.
MEMORIES = [
    (1, "Sacred Ground Ruins", -254.14, -97.91),
    (3, "Lake Kolomo", -681.08, 1223.99),
    (5, "Ancient Columns", -3501.04, -421.26),
    (7, "Kara Kara Bazaar", -3193.41, 2536.24),
    (8, "Eldin Canyon", 1417.29, -1537.95),
    (9, "Irch Plain", -1091.22, -1301.68),
    (11, "West Necluda", 1983.9, 1912.69),
    (12, "Hyrule Castle", -364.47, -995.87),
    (13, "Spring of Power", 3744.0, -2655.89),
    (14, "Sanidin Park Ruins", -1612.41, 688.02),
    (15, "Lanayru Road – East Gate", 3143.34, 1148.48),
    (16, "Hyrule Field", 700.66, 434.43),
    (17, "Ash Swamp", 173.27, 1935.49),
]

ZD_IMG = "https://www.zeldadungeon.net/wiki/images/"  # korok guide thumbnails


def proj(x, y):
    return round(2 * x + 12000, 1), round(2 * y + 10000, 1)


def main():
    t = open(ensure(SRC), encoding="utf-8", errors="replace").read()
    markers = []

    # ---- Korok hint table: { id, { "text", "image" } } ----
    info_re = re.compile(
        r'\{\s*(\d+)\s*,\s*\{\s*"((?:\\.|[^"\\])*)"\s*,\s*"([^"]*)"\s*\}\s*\}')
    infos = {int(m.group(1)): (m.group(2), m.group(3)) for m in info_re.finditer(t)}

    # ---- Koroks: Korok(hash, "internalName", x, y, zeldaId) ----
    korok_re = re.compile(
        r'\bKorok\(\s*(\d+)\s*,\s*"([^"]*)"\s*,\s*' + NUM + F + r'\s*,\s*' + NUM + F + r'\s*,\s*(\d+)\s*\)')
    for i, (hsh, iname, x, y, zid) in enumerate(korok_re.findall(t), 1):
        px, py = proj(float(x), float(y))
        hint, img = infos.get(int(zid), ("", ""))
        kt = "fly" if "Fly" in iname else "ground"
        m = dict(id=f"k{hsh}", cat="korok", name=f"Korok Seed #{i}", px=px, py=py, desc=hint, kt=kt)
        if img:
            m["img"] = ZD_IMG + img
        markers.append(m)

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
        if name.startswith("UMii") or name in CASTLE_ROOMS:
            continue
        px, py = proj(float(x), float(y))
        if name.endswith(" Tower"):
            cat, desc = "tower", "Sheikah Tower"
        elif name == "Great Fairy Fountain":
            who = min(GREAT_FAIRIES, key=lambda f: (proj(f[1], f[2])[0]-px)**2 + (proj(f[1], f[2])[1]-py)**2)[0]
            cat, name, desc = "fairy", f"Great Fairy {who}", "Great Fairy Fountain"
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

    # ---- Treasure chests + overworld enemies (Guardians/Lynels/Dragons) from map_locations.js ----
    loc = load_locations()
    GEMS = {"Opal", "Amber", "Topaz", "Sapphire", "Ruby", "Diamond", "Luminous Stone",
            "Flint", "Star Fragment", "Giant Ancient Core", "Ancient Core"}
    CHEST_OTHER = {"Travel Medallion", "Hestu's Maracas", "Korok Leaf", "Mighty Bananas", "Treasure Chest"}
    ARMOR_KW = ("Helm", "Cap", "Hood", "Mask", "Headwear", "Circlet", "Bandana", "Crown",
                "Tiara", "Armor", "Tunic", "Mail", "Shirt", "Doublet", "Vest", "Jacket",
                "Robe", "Trousers", "Greaves", "Boots", "Tights", "Leg Wraps", "Sandals",
                "Pants", "Skull", "Uniform")

    def chest_class(c):
        if "Rupee" in c:
            return "rupee"
        if "Arrow" in c:
            return "arrow"
        if c in GEMS or "Scale" in c or "Fang" in c:
            return "gem"          # gems, ores, dragon parts (materials)
        if c in CHEST_OTHER:
            return "other"
        if any(k in c for k in ARMOR_KW):
            return "armor"        # wearable armor -> its own top-level category
        return "gear"             # weapons, shields, bows

    ci = gi = li = di = ai = 0
    for key, e in loc.items():
        pts, nm = e["locations"], e["display_name"]
        if key.startswith("TBox"):
            content = nm.split(":", 1)[1] if ":" in nm else nm
            ct = chest_class(content)
            for x, z in pts:
                px, py = proj(x, z)
                if ct == "armor":
                    markers.append(dict(id=f"a{ai}", cat="armor", name=content, px=px, py=py,
                                        desc="Treasure chest")); ai += 1
                else:
                    markers.append(dict(id=f"c{ci}", cat="chest", name=content, px=px, py=py,
                                        desc="Treasure Chest", ct=ct)); ci += 1
        elif key.startswith("Enemy_Guardian"):
            for x, z in pts:
                px, py = proj(x, z)
                markers.append(dict(id=f"gd{gi}", cat="guardian", name=nm, px=px, py=py, desc="")); gi += 1
        elif key.startswith("Enemy_Lynel") and "_Far" not in key:
            label = nm.split(":")[0]
            for x, z in pts:
                px, py = proj(x, z)
                markers.append(dict(id=f"ly{li}", cat="lynel", name=label, px=px, py=py, desc="")); li += 1
        elif key.startswith("Enemy_Dragon") and "_Far" not in key and "_Grudge" not in key:
            for x, z in pts:
                px, py = proj(x, z)
                markers.append(dict(id=f"dr{di}", cat="dragon", name=nm, px=px, py=py,
                                    desc="Roams a regional circuit")); di += 1
    print(f"Loot: chests={ci} armor={ai} guardians={gi} lynels={li} dragons={di}")

    # ---- Armor: rich set/piece data + shop/quest set markers (from armor-sets.json) ----
    armor_path = os.path.join(ROOT, "armor-sets.json")
    if os.path.exists(armor_path):
        asets = json.load(open(armor_path, encoding="utf-8"))
        place_coords = {}
        for m in markers:                       # resolve a source "place" to existing marker coords
            place_coords.setdefault(m["name"], (m["px"], m["py"]))

        def find_place(name):
            if name in place_coords:
                return place_coords[name]
            for nm, c in place_coords.items():
                if name and (name in nm or nm in name):
                    return c
            return None

        def clean_src(x):                       # drop the merge agent's source-comparison notes
            x = re.sub(r"\s*\(Sources?\b[^)]*\)", "", x or "", flags=re.I)   # parenthesized notes
            parts = re.split(r"(?<=[.;]) +", x)                          # split into sentences
            parts = [p for p in parts if not re.search(r"\bsources?\b", p, re.I)]
            return re.sub(r"\s+", " ", " ".join(parts)).strip()

        armordata = {"pieces": {}, "sets": {}}
        for s in asets:
            src = clean_src(s.get("sourceText", ""))
            armordata["sets"][s["set"]] = {"pieces": s["pieces"], "bonus": s.get("setBonus", ""), "source": src}
            for p in s["pieces"]:
                armordata["pieces"][p["name"]] = {"set": s["set"].replace(" Set", "").strip(),
                                                  "slot": p.get("slot", ""), "defense": p.get("defense", 0),
                                                  "bonus": s.get("setBonus", ""), "source": src}

        # one marker per buyable/earnable SET at its source. Resolve a location from the `place`
        # field, else from a shrine/stable/town/landmark named in the source text (so scattered
        # sets like Climbing/Barbarian/Rubber land at one of their piece spots). Ring-jitter shares.
        CURATED = {"Champion's Tunic", "Thunder Helm", "Sand Boots", "Snow Boots", "Warm Doublet"}
        loc_markers = sorted(
            [(m["name"], (m["px"], m["py"])) for m in markers
             if m["cat"] in ("shrine", "dlcshrine", "tower", "town", "stable", "fairy", "lab", "region", "divinebeast")],
            key=lambda x: -len(x[0]))   # longest (most specific) names first

        KILTON = (15443.3, 12091.7)   # a central spot of Kilton's roaming Fang & Bone shop (Dark Set / masks)

        def resolve_loc(s):
            c = find_place(s.get("place", ""))
            if c:
                return c
            txt = s.get("sourceText", "")
            for nm, cc in loc_markers:
                if len(nm) >= 6 and nm in txt:
                    return cc
            if "Fang and Bone" in txt or "Kilton" in txt:
                return KILTON
            return None

        qualifying = [s for s in asets
                      if s["sourceType"] not in ("dlc_amiibo", "starting")     # amiibo pieces are already chest markers
                      and (len(s["pieces"]) >= 2 or s["set"] in CURATED)]
        byplace, skipped = {}, []
        for s in qualifying:
            c = resolve_loc(s)
            if c:
                byplace.setdefault(c, []).append(s)
            else:
                skipped.append(s["set"])
        asi = 0
        for c, group in sorted(byplace.items()):
            n = len(group)
            for i, s in enumerate(group):
                if n == 1:
                    px, py = c[0], c[1] - 55       # nudge above the source marker so they don't perfectly overlap
                else:
                    ang = 2 * math.pi * i / n
                    px, py = c[0] + 70 * math.cos(ang), c[1] + 70 * math.sin(ang)
                markers.append(dict(id=f"as{asi}", cat="armor", name=s["set"],
                                    px=round(px, 1), py=round(py, 1), desc="Armor set")); asi += 1
        print(f"Armor data: {len(armordata['pieces'])} pieces, {len(armordata['sets'])} sets, {asi} set markers placed")
        if skipped:
            print("  unplaced sets:", ", ".join(skipped))
        ad = "window.ARMORDATA = " + json.dumps(armordata, ensure_ascii=False, separators=(",", ":")) + ";\n"
        open(os.path.join(ROOT, "armordata.js"), "w", encoding="utf-8").write(
            "/* AUTO-GENERATED by tools/build_markers.py from armor-sets.json. */\n" + ad)

    # ---- Region assignment: nearest of the 15 Sheikah Towers (BotW's canonical map regions) ----
    towers = [(m["name"].replace(" Tower", ""), m["px"], m["py"]) for m in markers if m["cat"] == "tower"]
    for m in markers:
        m["region"] = min(towers, key=lambda tw: (tw[1]-m["px"])**2 + (tw[2]-m["py"])**2)[0]

    # ---- Categories (sidebar groups + icons/colors) ----
    categories = [
        dict(group="Progress", id="shrine", name="Shrines", icon="⛩️", color="#e8943c"),
        dict(group="Progress", id="dlcshrine", name="EX / DLC Shrines", icon="⛩️", color="#c062d0"),
        dict(group="Progress", id="tower", name="Sheikah Towers", icon="\U0001f5fc", color="#5ad1e6"),
        dict(group="Progress", id="divinebeast", name="Divine Beasts", icon="\U0001f409", color="#d14e8c"),
        dict(group="Collectibles", id="korok", name="Korok Seeds", icon="\U0001f343", color="#6fc24f"),
        dict(group="Treasure", id="chest", name="Treasure Chests", icon="\U0001f4b0", color="#d9b24a"),
        dict(group="Treasure", id="armor", name="Armor", icon="\U0001f9e5", color="#b486c9"),
        dict(group="Enemies", id="hinox", name="Hinox", icon="\U0001f479", color="#c0504d"),
        dict(group="Enemies", id="talus", name="Stone Talus", icon="\U0001faa8", color="#9a959a"),
        dict(group="Enemies", id="molduga", name="Molduga", icon="\U0001f988", color="#d9a441"),
        dict(group="Enemies", id="guardian", name="Guardians", icon="\U0001f47e", color="#d2674f"),
        dict(group="Enemies", id="lynel", name="Lynels", icon="\U0001f981", color="#a8472c"),
        dict(group="Enemies", id="dragon", name="Dragons", icon="\U0001f432", color="#76b88a"),
        dict(group="Places", id="town", name="Towns & Villages", icon="\U0001f3d8️", color="#5b9bd5"),
        dict(group="Places", id="stable", name="Stables", icon="\U0001f434", color="#b07a4a"),
        dict(group="Places", id="fairy", name="Great Fairy Fountains", icon="\U0001f9da", color="#ff7fd0"),
        dict(group="Places", id="lab", name="Ancient Tech Labs", icon="\U0001f52c", color="#3d9970"),
        dict(group="Reference", id="region", name="Location Labels", icon="\U0001f4cd", color="#7c879b"),
    ]

    # ---- counts report ----
    from collections import Counter
    cnt = Counter(m["cat"] for m in markers)
    kt = Counter(m.get("kt") for m in markers if m["cat"] == "korok")
    reg = Counter(m["region"] for m in markers)
    print("Markers by category:")
    for c in categories:
        print(f"  {c['id']:12} {cnt.get(c['id'], 0)}")
    print(f"  {'TOTAL':12} {len(markers)}")
    print(f"Korok types: ground={kt['ground']} fly={kt['fly']}")
    print("Per-region totals:")
    for r, n in sorted(reg.items(), key=lambda kv: -kv[1]):
        print(f"  {r:16} {n}")

    # ---- write markers.js ----
    lines = ["/* AUTO-GENERATED by tools/build_markers.py — datamined BotW markers.",
             "   Source: lud99/botw-unexplored Data.cpp (game-world coords).",
             "   px,py = pixel on the 24000x20000 objmap tile image: px=2x+12000, py=2y+10000.",
             "   region = nearest Sheikah Tower; kt = korok ground/fly. */",
             "", "const CATEGORIES = ["]
    for c in categories:
        lines.append("  " + json.dumps(c, ensure_ascii=False) + ",")
    lines += ["];", "", "const MARKERS = ["]
    for m in markers:
        lines.append("  " + json.dumps(m, ensure_ascii=False) + ",")
    lines.append("];")
    open(OUT, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print(f"\nWrote {OUT} ({os.path.getsize(OUT)/1024:.0f} KB, {len(markers)} markers)")

    # ---- write quests.js (Captured Memories route) ----
    steps = []
    for n, (album, loc, x, y) in enumerate(MEMORIES, 1):
        px, py = proj(x, y)
        steps.append(dict(n=n, title=loc, desc=f"Captured Memory (album #{album})",
                          kind="memory", px=px, py=py))
    quest = dict(id="memories", name="Captured Memories", color="#e8d39c", steps=steps)
    qlines = ["/* AUTO-GENERATED by tools/build_markers.py — ordered routes (questlines). */",
              "", "window.QUESTLINES = [", "  " + json.dumps(quest, ensure_ascii=False), "];"]
    open(QOUT, "w", encoding="utf-8").write("\n".join(qlines) + "\n")
    print(f"Wrote {QOUT} ({len(steps)} memory steps)")


if __name__ == "__main__":
    main()
