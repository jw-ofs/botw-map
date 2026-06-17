# Breath of the Wild — Interactive Map

A self-contained, **fully offline** Map-Genie–style interactive map of Hyrule, built with Leaflet.
Double-click `index.html` (or serve the folder) and explore — tiles, data, and library are all local.

![categories](https://img.shields.io/badge/markers-1303-5ad1e6) shrines · towers · koroks · enemies · places

## Run it

- **Quickest:** open `index.html` in a browser. (If tiles don't show over `file://`, serve instead.)
- **Served:** `python -m http.server 8799` then visit <http://localhost:8799>.

> The `tiles/` folder (~44 MB) is **git-ignored**. On a fresh clone, regenerate it once with
> `python tools/build_tiles.py` before the terrain will render.

## Features

- **1,303 datamined markers** across 14 categories (see below), pixel-accurate to the map.
- Marker **clustering** that declutters at low zoom; individual pins at full zoom.
- **Progress tracking** — click "Mark as found"; saved to `localStorage`, with a live completion %.
- **Search** with fly-to, **category filters**, **hide-found**, **export/import** progress as JSON,
  and **share-view** (URL hash + clipboard).
- Korok pins show the in-game **hint text**; location names render as fading text labels.

## Categories

| Group | Categories |
|---|---|
| Progress | Shrines (120), EX/DLC Shrines (16), Sheikah Towers (15), Divine Beasts (4) |
| Collectibles | Korok Seeds (900) |
| Enemies | Hinox (40), Stone Talus (40), Molduga (4) |
| Places | Towns & Villages, Stables, Great Fairy Fountains (4), Ancient Tech Labs |
| Reference | Location Labels (134, as text) |

## How it works

| Concern | Detail |
|---|---|
| Base tiles | Datamined Hyrule map, **24000×20000 px**, `tileSize 256`, native zoom 7. Sourced from [objmap](https://objmap.zeldamods.org) and stored locally as webp at `tiles/{z}/{x}/{y}.webp`. |
| Markers | From [`lud99/botw-unexplored`](https://github.com/lud99/botw-unexplored) `Data.cpp` (game-world coords). |
| Projection | `px = 2·x + 12000`, `py = 2·y + 10000` (1 game unit = 2 px, world origin = image center). Leaflet placement: `xy(px,py) = L.latLng(-py/128, px/128)` on `CRS.Simple`. |

## Regenerate the data

```bash
python tools/build_tiles.py     # download + webp the z0-7 tile pyramid -> tiles/
python tools/build_markers.py   # parse Data.cpp -> markers.js
```

`tools/build_markers.py` also reads an optional `_cache/memories.json`
(`[{ "n":1, "name":"…", "x":…, "y":… }]`) to populate the Captured Memories category.

## Credits

Map tiles & object data are community datamining efforts: **ZeldaMods / objmap** and
**lud99/botw-unexplored**. This project is a non-commercial fan tool. *Breath of the Wild*
is © Nintendo.
