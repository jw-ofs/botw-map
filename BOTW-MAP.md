# Breath of the Wild — Interactive Map

A self-contained, **fully offline** Map-Genie–style interactive map of Hyrule, built with Leaflet.
Double-click `index.html` (or serve the folder) and explore — tiles, data, and library are all local.

![categories](https://img.shields.io/badge/markers-2684-5ad1e6) shrines · towers · koroks · treasure · enemies · places · memories route

## ▶ Play it live

**https://jw-ofs.github.io/botw-map/** — open in any browser, on desktop or phone. Share away.

## Run it locally

- **Quickest:** open `index.html` in a browser.
- **Served:** `python -m http.server 8799` then visit <http://localhost:8799>.

> The z0–7 tile pyramid (~44 MB) is committed so the site is self-contained (GitHub Pages serves it).
> Regenerate the tiles anytime with `python tools/build_tiles.py`.

## Features

- **2,684 datamined markers** across 18 categories (see below), pixel-accurate to the map.
- **Per-region completion** — every marker assigned to its nearest Sheikah Tower; collapsible
  bars track progress across all 15 regions, click to fly there.
- **Captured Memories route** — the 13 memory spots as an ordered questline (numbered pins +
  dashed path + step-by-step side panel), under the *Routes* group.
- **Korok seeds** split into **Ground / Flight** sub-filters; each pin shows its in-game **hint
  text** and **guide thumbnail**.
- **Treasure chests** (1,165) with itemized contents and a Rupees/Gems/Arrows/Gear/Other
  sub-filter, plus a dedicated **Armor** category (48 — 32 chest pieces + 16 buyable/earnable
  sets, each popup showing the set, slot, base defense, set bonus, and source — `armordata.js`); plus
  **Guardians** (154), **Lynels** (26), and the **3 Dragons**.
- **Shrine info popups** — type (Tutorial / Test of Strength / Blessing / Puzzle / Combat), chest
  reward, and the unlocking Shrine Quest for all **120 shrines** (`shrinedata.js`, sourced and
  cross-verified from community wikis — 118/120 types independently agreed).
- **Enemy combat popups** — weaknesses, damage dealt, and a strategy tip for Hinox / Stone Talus /
  Molduga / Guardians / Lynels / Dragons (`bossdata.js`).
- **Per-marker notes** — jot a reminder on any pin (a cyan dot marks noted pins); saved and
  included in export/import.
- **Bulk actions** — "Mark visible" / "Clear visible" over the current filter, plus **Reset**,
  all with a one-tap **Undo** toast.
- Marker **clustering**; **progress tracking** (localStorage) with a live completion %.
- **Search** with fly-to, **category filters**, **hide-found**, **export/import** JSON,
  **share-view**, **deep-links** to a single marker (🔗 in any popup), and hover tooltips.

## Categories

| Group | Categories |
|---|---|
| Progress | Shrines (120), EX/DLC Shrines (16), Sheikah Towers (15), Divine Beasts (4) |
| Collectibles | Korok Seeds (900 — Ground/Flight filter, hint + thumbnail) |
| Treasure | Treasure Chests (1,165 — content filter: Rupees / Gems / Arrows / Gear / Other), Armor (48 — chest pieces + buyable/earnable sets, with set bonus / slot / defense / source) |
| Enemies | Hinox (40), Stone Talus (40), Molduga (4), Guardians (154), Lynels (26), Dragons (3) |
| Places | Towns & Villages (9), Stables (15), Great Fairy Fountains (4, named), Ancient Tech Labs (2) |
| Reference | Location Labels (119, as text — Hyrule Castle interior rooms excluded) |
| Routes | Captured Memories (13 ordered steps) |

## How it works

| Concern | Detail |
|---|---|
| Base tiles | Datamined Hyrule map, **24000×20000 px**, `tileSize 256`, native zoom 7. Sourced from [objmap](https://objmap.zeldamods.org) and stored locally as webp at `tiles/{z}/{x}/{y}.webp`. |
| Markers | From [`lud99/botw-unexplored`](https://github.com/lud99/botw-unexplored) `Data.cpp` (game-world coords); Memories & Great Fairy names cross-referenced from [`MrCheeze/botw-object-map`](https://github.com/MrCheeze/botw-object-map) `map_locations.js`. |
| Regions | Each marker assigned to the nearest of the 15 Sheikah Towers — BotW's canonical map regions. |
| Projection | `px = 2·x + 12000`, `py = 2·y + 10000` (1 game unit = 2 px, world origin = image center). Leaflet placement: `xy(px,py) = L.latLng(-py/128, px/128)` on `CRS.Simple`. |

## Regenerate the data

```bash
python tools/build_tiles.py     # download + webp the z0-7 tile pyramid -> tiles/
python tools/build_markers.py   # parse Data.cpp -> markers.js + quests.js
```

`build_markers.py` emits both `markers.js` (categories + markers, each with `region`, koroks with
`kt`/`img`) and `quests.js` (the Captured Memories route). Memory and Great Fairy coordinates are
hardcoded constants in the script (verified against landmarks).

## Credits

Map tiles & object data are community datamining efforts: **ZeldaMods / objmap** and
**lud99/botw-unexplored**. This project is a non-commercial fan tool. *Breath of the Wild*
is © Nintendo.
