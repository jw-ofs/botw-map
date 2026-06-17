#!/usr/bin/env python3
"""Download the datamined Breath of the Wild map tile pyramid (z0-7) from the
zeldamods objmap server and store it locally as webp for a fully offline map.

Source tiles : https://objmap.zeldamods.org/game_files/maptex/{z}/{x}/{y}.png
Map image    : 24000 x 20000 px, tileSize 256, native max zoom 7.
Output       : tiles/{z}/{x}/{y}.webp   (PNG -> webp, ~50% smaller)

Idempotent: existing output tiles are skipped, so the run resumes if interrupted.
"""
import io
import os
import sys
import math
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "tiles")
LOG = os.path.join(ROOT, "_cache", "tiles.log")
BASE = "https://objmap.zeldamods.org/game_files/maptex"
MAP_W, MAP_H, TILE, NZ = 24000, 20000, 256, 7
WORKERS = 24
QUALITY = 82


def grid(z):
    scale = 2 ** (z - NZ)
    cols = math.ceil(MAP_W * scale / TILE)
    rows = math.ceil(MAP_H * scale / TILE)
    return cols, rows


def all_tiles():
    for z in range(0, NZ + 1):
        cols, rows = grid(z)
        for x in range(cols):
            for y in range(rows):
                yield z, x, y


def fetch(z, x, y):
    out = os.path.join(OUT, str(z), str(x), f"{y}.webp")
    if os.path.exists(out):
        return "skip"
    url = f"{BASE}/{z}/{x}/{y}.png"
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "botw-map-builder"})
            with urllib.request.urlopen(req, timeout=40) as r:
                data = r.read()
            img = Image.open(io.BytesIO(data)).convert("RGB")
            os.makedirs(os.path.dirname(out), exist_ok=True)
            img.save(out, "WEBP", quality=QUALITY, method=4)
            return "ok"
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return "404"
            time.sleep(0.5 * (attempt + 1))
        except Exception:
            time.sleep(0.5 * (attempt + 1))
    return "fail"


def main():
    tiles = list(all_tiles())
    total = len(tiles)
    counts = {"ok": 0, "skip": 0, "404": 0, "fail": 0}
    t0 = time.time()
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "w", encoding="utf-8") as log:
        log.write(f"Downloading {total} tiles (z0-{NZ}) -> {OUT}\n")
        log.flush()
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            futs = {ex.submit(fetch, *t): t for t in tiles}
            done = 0
            for fut in as_completed(futs):
                counts[fut.result()] += 1
                done += 1
                if done % 250 == 0 or done == total:
                    el = time.time() - t0
                    rate = done / el if el else 0
                    eta = (total - done) / rate if rate else 0
                    line = (f"{done}/{total}  ok={counts['ok']} skip={counts['skip']} "
                            f"404={counts['404']} fail={counts['fail']}  "
                            f"{rate:.0f}/s  eta {eta/60:.1f}m")
                    log.write(line + "\n")
                    log.flush()
                    print(line, flush=True)
    # final size
    size = sum(os.path.getsize(os.path.join(dp, f))
               for dp, _, fs in os.walk(OUT) for f in fs)
    with open(LOG, "a", encoding="utf-8") as log:
        log.write(f"DONE in {(time.time()-t0)/60:.1f}m  size={size/1e6:.1f} MB  {counts}\n")
    print(f"DONE  size={size/1e6:.1f} MB  {counts}", flush=True)


if __name__ == "__main__":
    main()
