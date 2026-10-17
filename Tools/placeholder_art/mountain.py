#!/usr/bin/env python3
"""
Placeholder mountains (example for big multi-tile props).

Writes Art/Props/mountain.png (6x6-tile footprint) and Art/Props/mountain_small.png (4x4) and adds/updates
their entries in Art/Props/props.json without touching the other entries.

    Tools/.venv/bin/python Tools/placeholder_art/mountain.py
"""
import json
import math
import os

import numpy as np

from generate import ART, Model, render

PROPS_JSON = os.path.join(ART, "Props", "props.json")


def periodic_noise(x, y, seed, scale):
    """Cheap smooth noise from a few random sine waves (good enough for rock shapes)."""
    r = np.random.default_rng(seed)
    total = np.zeros_like(x)
    for _ in range(6):
        a, ph = r.random() * math.pi, r.random() * 10
        f = scale * (0.5 + r.random())
        total += np.sin((x * math.cos(a) + y * math.sin(a)) * f + ph)
    return total / 6


def mountain(m, radius, height, seed):
    # heightfield over a disk, sampled on a fine grid (units = ground pixels)
    step = 0.3
    g = np.arange(-radius, radius + step, step)
    x, y = np.meshgrid(g, g)
    x, y = x.ravel(), y.ravel()
    r = np.hypot(x, y)
    edge = radius * (1 + 0.12 * periodic_noise(x, y, seed + 1, 0.03))   # wobbly outline
    keep = r < edge
    x, y, r, edge = x[keep], y[keep], r[keep], edge[keep]

    t = np.clip(1 - r / edge, 0, 1)
    ridges = np.abs(periodic_noise(x, y, seed + 2, 0.06))               # sharp ridge lines
    z = height * (t ** 1.15) * (0.8 + 0.35 * ridges) + 4 * periodic_noise(x, y, seed + 3, 0.25)
    z = np.maximum(z, 0)

    # normals from the height gradient (finite differences on the same formula)
    def h(px, py):
        rr = np.hypot(px, py)
        ee = radius * (1 + 0.12 * periodic_noise(px, py, seed + 1, 0.03))
        tt = np.clip(1 - rr / ee, 0, 1)
        rid = np.abs(periodic_noise(px, py, seed + 2, 0.06))
        return np.maximum(height * (tt ** 1.15) * (0.8 + 0.35 * rid) + 4 * periodic_noise(px, py, seed + 3, 0.25), 0)

    d = 0.8
    dzdx = (h(x + d, y) - h(x - d, y)) / (2 * d)
    dzdy = (h(x, y + d) - h(x, y - d)) / (2 * d)
    nrm = np.stack([-dzdx, -dzdy, np.ones_like(z)], 1)

    # colours: dark rock at the bottom, grey higher up, snow on the upper, flatter parts
    rock_low = np.array([95, 88, 82])
    rock_high = np.array([130, 128, 132])
    k = (z / height)[:, None]
    col = rock_low * (1 - k) + rock_high * k
    up = nrm[:, 2] / np.linalg.norm(nrm, axis=1)
    snow = (z > height * (0.5 + 0.1 * periodic_noise(x, y, seed + 4, 0.08))) & (up > 0.45)
    col[snow] = np.array([238, 242, 250])
    pts = np.stack([x, y, z], 1)
    m.add(pts, nrm, col, tex=0.1)


# name: (radius in ground px, height px, seed, image w, h, pivot, collider radius in world units, footprint cells)
MOUNTAINS = {
    "mountain": (125, 235, 7, 300, 300, (150, 72), 1.75, 6),
    "mountain_small": (82, 150, 21, 200, 220, (100, 50), 1.15, 4),
}


def main():
    with open(PROPS_JSON) as fh:
        data = json.load(fh)
    data["props"] = [p for p in data["props"] if p["name"] not in MOUNTAINS]
    for name, (radius, height, seed, w, hgt, pivot, col_r, cells) in MOUNTAINS.items():
        m = Model()
        mountain(m, radius, height, seed)
        render(m, w, hgt, pivot).save(os.path.join(ART, "Props", f"{name}.png"))
        offset = 0.5 if cells % 2 == 0 else 0.0  # even footprints centre on a tile corner
        data["props"].append(dict(name=name, pivotX=pivot[0], pivotY=pivot[1], fade=True,
                                  colliderType="ellipse", radius=col_r, halfWidth=0, halfHeight=0,
                                  offsetX=offset, offsetY=offset))
        print(f"prop {name}: {w}x{hgt}px, footprint {cells}x{cells} tiles")
    with open(PROPS_JSON, "w") as fh:
        json.dump(data, fh, indent=2)


if __name__ == "__main__":
    main()
