#!/usr/bin/env python3
"""
Writes the starting region maps to Assets/Resources/Regions/*.txt.
These are meant as a first draft: after generating once, edit the .txt files by hand.
Re-running this script OVERWRITES them.
"""
import math
import os
import random

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "Assets", "Resources", "Regions")

HEADER = """# Region map. Format:
#   name: / ambient:   region display name and ambient light tint (r g b, 0-1)
#   [legend]           <char> <ground tile> [object]
#                      object = prop name (see Art/Props/props.json) | npc:<id> | enemy:<id>
#                               | entry:<id> | exit:<region>:<entry id>
#   [map]              one character per cell. Text column = grid X, text row = grid Y (top row = far side).
# In game the map is rotated 45 deg: the TOP-RIGHT of this text is the top of the screen.
"""


class Grid:
    def __init__(self, w, h, fill):
        self.w, self.h = w, h
        self.c = [[fill] * w for _ in range(h)]

    def __getitem__(self, xy):
        x, y = xy
        return self.c[y][x]

    def __setitem__(self, xy, v):
        x, y = xy
        if 0 <= x < self.w and 0 <= y < self.h:
            self.c[y][x] = v

    def disk(self, cx, cy, r, ch, only=None):
        for y in range(self.h):
            for x in range(self.w):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r and (only is None or self[x, y] in only):
                    self[x, y] = ch

    def ellipse(self, cx, cy, rx, ry, ch):
        for y in range(self.h):
            for x in range(self.w):
                if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1:
                    self[x, y] = ch

    def path(self, pts, ch, width=2, keep=()):
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            steps = max(abs(x1 - x0), abs(y1 - y0))
            for i in range(steps + 1):
                x = round(x0 + (x1 - x0) * i / max(steps, 1))
                y = round(y0 + (y1 - y0) * i / max(steps, 1))
                for ox in range(width):
                    for oy in range(width):
                        if self[min(x + ox, self.w - 1), min(y + oy, self.h - 1)] not in keep:
                            self[x + ox, y + oy] = ch

    def text(self):
        return "\n".join("".join(row) for row in self.c)


def write(name, title, ambient, legend, grid):
    os.makedirs(OUT, exist_ok=True)
    lines = [HEADER, f"name: {title}", f"ambient: {ambient}", "", "[legend]"]
    lines += [f"{k} {v}" for k, v in legend.items()]
    lines += ["", "[map]", grid.text(), ""]
    with open(os.path.join(OUT, f"{name}.txt"), "w") as fh:
        fh.write("\n".join(lines))
    print("region", name, f"{grid.w}x{grid.h}")


# Text rows run top->bottom, so y=0 here is the TOP row (far side of the map).
def forest():
    random.seed(11)
    W = H = 46
    g = Grid(W, H, "f")
    # scatter forest
    for y in range(H):
        for x in range(W):
            edge = min(x, y, W - 1 - x, H - 1 - y)
            p = 0.9 if edge < 2 else 0.55 if edge < 3 else 0.14
            if random.random() < p:
                g[x, y] = random.choice("TTP")
            elif random.random() < 0.02:
                g[x, y] = "k"
    # village clearing
    g.disk(23, 24, 10, ".")
    for _ in range(40):
        g[random.randint(14, 32), random.randint(15, 33)] = "," if random.random() < 0.7 else "."
    # pond
    g.ellipse(10, 27, 4.5, 3.2, "~")
    g.disk(10, 27, 6, ".", only="fTPk")
    # paths: village -> north exit (snow) and -> east exit (desert), plus a loop to the bandit camp
    g.path([(23, 24), (22, 14), (20, 6), (20, 0)], ":")
    g.path([(23, 24), (32, 22), (39, 20), (45, 20)], ":")
    g.path([(23, 24), (24, 33), (30, 38)], ":")
    # houses (2x2 footprint anchored on the marked cell)
    for hx, hy in ((16, 18), (28, 17), (17, 28), (29, 28)):
        for ox in range(-1, 3):
            for oy in range(-1, 3):
                if g[hx + ox, hy + oy] not in ":":
                    g[hx + ox, hy + oy] = "."
        g[hx, hy] = "H"
    for x, y in ((14, 21), (31, 20), (20, 31), (33, 26), (26, 31)):
        g[x, y] = random.choice("bbr")
    g[23, 24] = "W"
    g[25, 25] = "@"
    g[21, 23] = "a"
    g[27, 20] = "m"
    g[21, 15] = "g"
    # bandit camp in the south-east
    g.disk(32, 39, 4, ".", only="fTPk")
    g[32, 39] = "F"
    g[30, 40] = "x"
    g[34, 38] = "x"
    # wolf clearings
    g.disk(9, 9, 4, "f", only="TPk")
    g.disk(37, 9, 4, "f", only="TPk")
    for x, y in ((8, 8), (10, 10), (36, 8), (38, 10), (37, 11)):
        g[x, y] = "w"
    # exits and arrival points
    for x in (20, 21):
        g[x, 0] = "1"
    g[20, 3] = "n"
    for y in (20, 21):
        g[45, y] = "2"
    g[42, 20] = "e"
    legend = {
        ".": "grass", ",": "grass_flowers", "f": "forest_floor", ":": "path", "~": "water",
        "T": "forest_floor tree_oak", "P": "forest_floor tree_pine", "b": "grass bush", "r": "grass rock",
        "k": "forest_floor rock", "H": "grass house", "W": "path well", "F": "grass campfire",
        "@": "path entry:start", "n": "path entry:from_snow", "e": "path entry:from_desert",
        "1": "path exit:snow:from_forest", "2": "path exit:desert:from_forest",
        "a": "grass npc:elder", "m": "grass npc:merchant", "g": "path npc:guard",
        "w": "forest_floor enemy:wolf", "x": "grass enemy:bandit",
    }
    write("forest", "Greenhollow", "1 1 1", legend, g)


def desert():
    random.seed(22)
    W = H = 46
    g = Grid(W, H, ".")
    for y in range(H):
        for x in range(W):
            n = math.sin(x * 0.31 + y * 0.12) + math.sin(y * 0.27 - x * 0.08 + 2) + 0.5 * math.sin(x * 0.7 + y * 0.6)
            if n > 0.9:
                g[x, y] = "d"
            elif n < -1.3:
                g[x, y] = "c"
            if random.random() < 0.035:
                g[x, y] = "C"
            elif random.random() < 0.03:
                g[x, y] = "R"
            edge = min(x, y, W - 1 - x, H - 1 - y)
            if edge < 2 and random.random() < 0.6:
                g[x, y] = random.choice("RRC")
    # oasis
    g.disk(28, 24, 7, "g")
    g.ellipse(28, 24, 4, 3, "~")
    for a in range(0, 360, 40):
        x = round(28 + math.cos(math.radians(a)) * 6)
        y = round(24 + math.sin(math.radians(a)) * 5.5)
        g[x, y] = "p"
    g.path([(0, 21), (12, 22), (21, 23)], ":")
    g[22, 18] = "t"
    g[21, 20] = "z"
    g[20, 18] = "F"
    # scorpions & bandits
    for x, y in ((10, 10), (12, 11), (35, 8), (37, 37), (14, 36), (16, 38), (40, 28)):
        g[x, y] = "s"
    for x, y in ((33, 38), (35, 40)):
        g[x, y] = "x"
    for y in (21, 22):
        g[0, y] = "1"
    g[3, 21] = "w"
    legend = {
        ".": "sand", "d": "dune", "c": "cracked_earth", ":": "cracked_earth", "~": "water", "g": "grass",
        "C": "sand cactus", "R": "sand rock_sand", "p": "grass palm", "t": "sand tent", "F": "sand campfire",
        "z": "grass npc:nomad", "s": "sand enemy:scorpion", "x": "sand enemy:bandit",
        "w": "cracked_earth entry:from_forest", "1": "cracked_earth exit:forest:from_desert",
    }
    write("desert", "Sunscar Wastes", "1 0.97 0.9", legend, g)


def snow():
    random.seed(33)
    W = H = 46
    g = Grid(W, H, ".")
    for y in range(H):
        for x in range(W):
            edge = min(x, y, W - 1 - x, H - 1 - y)
            p = 0.85 if edge < 2 else 0.18
            if random.random() < p:
                g[x, y] = "P"
            elif random.random() < 0.03:
                g[x, y] = "R"
    # frozen lake
    g.ellipse(14, 16, 8, 6, "i")
    # hunter camp
    g.disk(30, 14, 6, ".")
    g[29, 11] = "H"
    for ox in range(-1, 3):
        for oy in range(-1, 3):
            if (ox, oy) != (0, 0):
                g[29 + ox, 11 + oy] = "."
    g[31, 15] = "F"
    g[29, 15] = "h"
    g.path([(20, 45), (22, 30), (28, 18)], ":")
    for x, y in ((10, 30), (12, 32), (36, 30), (38, 33), (8, 6), (37, 6), (39, 8)):
        g[x, y] = "w"
    for x in (20, 21):
        g[x, 45] = "1"
    g[20, 42] = "s"
    legend = {
        ".": "snow", ":": "snow_path", "i": "ice", "P": "snow tree_pine_snow", "R": "snow rock_snow",
        "H": "snow house", "F": "snow campfire", "h": "snow npc:hunter", "w": "snow enemy:frost_wolf",
        "s": "snow_path entry:from_forest", "1": "snow_path exit:forest:from_snow",
    }
    write("snow", "Frostpeak Pass", "0.92 0.96 1.05", legend, g)


if __name__ == "__main__":
    forest()
    desert()
    snow()
