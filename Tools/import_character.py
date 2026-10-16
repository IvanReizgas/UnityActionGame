#!/usr/bin/env python3
"""
Import an 8-direction character export (e.g. a PixelLab zip with rotations/<direction>.png)
into the game's sheet format (see ART_SPEC.md).

    Tools/.venv/bin/python Tools/import_character.py <export.zip or folder> <character name> [--portrait NAME]
        [--anim walk="path/to/name_walking_{dir}.gif"] [--fps walk=10]

--anim takes one animated GIF (or PNG strip) per direction; {dir} is replaced by
south, south-west, west, north-west, north, north-east, east, south-east.

- Uses the export's own animation frames when it has them (any animation whose name contains
  "idle", "walk" or "attack"/"slash").
- Otherwise builds placeholder animations from the single rotation pose:
    idle   = breathing (upper body bobs 1px)
    walk   = body bob + alternating leg lift / stride shear (rough!)
    attack = forward lunge (the game adds a slash effect on the hit frame)
- Also writes a head-and-shoulders portrait from the south-facing pose.
- Keeps a copy of the source files in ArtSource/<name>/ (not shipped with the game).
"""
import argparse
import json
import math
import os
import shutil
import tempfile
import zipfile

from PIL import ImageSequence

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART = os.path.join(ROOT, "Assets", "Resources", "Art")

# game row order and the export's direction names
DIRS = ["south", "south-west", "west", "north-west", "north", "north-east", "east", "south-east"]
# screen-space unit vector for each direction (x right, y up)
DIR_VEC = {d: (math.cos(math.radians(a)), math.sin(math.radians(a)))
           for d, a in zip(DIRS, [270, 225, 180, 135, 90, 45, 0, 315])}

FRAME = 80          # output frame size (room for wide poses like slides)
PIVOT = (40, 6)     # feet position in the output frame, from bottom-left


def load_source(src):
    if zipfile.is_zipfile(src):
        tmp = tempfile.mkdtemp()
        with zipfile.ZipFile(src) as z:
            z.extractall(tmp)
        return tmp
    return src


def find_metadata(folder):
    for dirpath, _, files in os.walk(folder):
        if "metadata.json" in files:
            with open(os.path.join(dirpath, "metadata.json")) as fh:
                return dirpath, json.load(fh)
    return folder, None


def find_rotations(folder):
    for dirpath, dirs, files in os.walk(folder):
        if os.path.basename(dirpath) == "rotations" and "south.png" in files:
            return {d: os.path.join(dirpath, f"{d}.png") for d in DIRS if f"{d}.png" in files}
    raise SystemExit("No rotations/<direction>.png found in the export")


def export_animations(base, meta):
    """Returns {anim_kind: {direction: [paths]}} for animations included in the export."""
    out = {}
    if not meta:
        return out
    for state in meta.get("states", []):
        anims = state.get("frames", {}).get("animations", {}) or {}
        for name, per_dir in anims.items():
            kind = ("walk" if "walk" in name.lower() or "run" in name.lower() else
                    "attack" if "attack" in name.lower() or "slash" in name.lower() else
                    "idle" if "idle" in name.lower() or "breath" in name.lower() else None)
            if kind and isinstance(per_dir, dict):
                frames = {d: [os.path.join(base, p) for p in (v if isinstance(v, list) else [v])]
                          for d, v in per_dir.items() if d in DIRS}
                if len(frames) == 8:
                    out.setdefault(kind, frames)
    return out


def gif_frames(path):
    """All frames of an animated GIF (or a single image) as RGBA arrays, plus the frame duration in ms."""
    im = Image.open(path)
    frames = [np.array(f.convert("RGBA")) for f in ImageSequence.Iterator(im)]
    return frames, im.info.get("duration", 100)


def rgba(path):
    return np.array(Image.open(path).convert("RGBA"))


def bbox(img):
    ys, xs = np.nonzero(img[:, :, 3] > 0)
    return xs.min(), xs.max(), ys.min(), ys.max()


def feet_anchor(img):
    """x centre of the lowest opaque rows, and the lowest opaque row."""
    a = img[:, :, 3] > 0
    ys = np.nonzero(a.any(axis=1))[0]
    bottom = ys.max()
    rows = a[max(0, bottom - 3):bottom + 1]
    xs = np.nonzero(rows.any(axis=0))[0]
    return (xs.min() + xs.max()) / 2, bottom


def place(img, anchor_x, bottom, dx=0, dy=0):
    """Paste img into an output frame so its feet land on the pivot, plus an extra offset (dy up = +)."""
    frame = np.zeros((FRAME, FRAME, 4), np.uint8)
    ox = int(round(PIVOT[0] - anchor_x)) + dx
    oy = (FRAME - 1 - PIVOT[1]) - bottom - dy
    h, w = img.shape[:2]
    for y in range(h):
        ty = y + oy
        if not 0 <= ty < FRAME:
            continue
        for x in range(w):
            tx = x + ox
            if 0 <= tx < FRAME and img[y, x, 3] > 0:
                frame[ty, tx] = img[y, x]
    return frame


def shift_region(img, y0, y1, dx, dy, x_mask=None):
    """Move the pixels of rows [y0, y1) (optionally only columns in x_mask) by (dx, dy) image pixels."""
    out = img.copy()
    region = np.zeros_like(img)
    region[y0:y1] = img[y0:y1]
    if x_mask is not None:
        region[:, ~x_mask] = 0
    out[region[:, :, 3] > 0] = 0
    moved = np.roll(np.roll(region, dy, axis=0), dx, axis=1)
    m = moved[:, :, 3] > 0
    out[m] = moved[m]
    return out


def breathe(img, top, waist, amount):
    return shift_region(img, top, waist, 0, amount) if amount else img


def walk_frame(img, d, phase, top, waist, bottom, anchor_x):
    """Rough procedural walk: alternating foot lift + stride shear on the lower legs, body bob."""
    vx, vy = DIR_VEC[d]
    s = math.sin(phase)
    out = img.copy()
    knee = waist + (bottom - waist) // 2
    cols = np.arange(img.shape[1])
    left = cols < anchor_x
    right = ~left
    side_view = abs(vx) > 0.6
    if side_view:
        # stride: front half of the lower legs moves forward, back half backward
        fwd = (cols - anchor_x) * np.sign(vx) > 0
        step = int(round(2 * s))
        out = shift_region(out, knee, bottom + 1, step * int(np.sign(vx)), 0, fwd)
        out = shift_region(out, knee, bottom + 1, -step * int(np.sign(vx)), 0, ~fwd)
    else:
        # front/back/diagonal: lift one foot, then the other
        lift = int(round(2 * max(0.0, s)))
        lift2 = int(round(2 * max(0.0, -s)))
        out = shift_region(out, knee, bottom + 1, 0, -lift, left)
        out = shift_region(out, knee, bottom + 1, 0, -lift2, right)
        # diagonals also get a little stride
        if abs(vx) > 0.3:
            step = int(round(1 * s))
            out = shift_region(out, knee, bottom + 1, step, 0, left)
            out = shift_region(out, knee, bottom + 1, -step, 0, right)
    bob = 1 if abs(s) > 0.5 else 0  # body dips when legs are apart
    out = shift_region(out, top, waist, 0, bob)
    return out


def build(src, name, portrait_name, anim_files=None, fps_override=None):
    folder = load_source(src)
    base, meta = find_metadata(folder)
    rotations = find_rotations(folder)
    if len(rotations) < 8:
        missing = [d for d in DIRS if d not in rotations]
        raise SystemExit(f"Missing directions: {missing}")
    poses = {d: rgba(p) for d, p in rotations.items()}
    provided = export_animations(base, meta)
    fps_override = fps_override or {}
    gif_anims = {}
    for kind, pattern in (anim_files or {}).items():
        per_dir, dur = {}, 100
        for d in DIRS:
            path = os.path.expanduser(pattern.replace("{dir}", d))
            if not os.path.exists(path):
                raise SystemExit(f"--anim {kind}: missing {path}")
            per_dir[d], dur = gif_frames(path)
        gif_anims[kind] = (per_dir, dur)

    out_dir = os.path.join(ART, "Characters", name)
    os.makedirs(out_dir, exist_ok=True)
    anims = []

    def write(kind, frames_by_dir, fps, loop, hit=-1, source=None):
        n = len(frames_by_dir[DIRS[0]])
        sheet = np.zeros((FRAME * 8, FRAME * n, 4), np.uint8)
        for r, d in enumerate(DIRS):
            for f, fr in enumerate(frames_by_dir[d]):
                sheet[r * FRAME:(r + 1) * FRAME, f * FRAME:(f + 1) * FRAME] = fr
        Image.fromarray(sheet, "RGBA").save(os.path.join(out_dir, f"{kind}.png"))
        anims.append(dict(name=kind, file=kind, frames=n, fps=fps, loop=loop, hitFrame=hit))
        source = source or ("from export" if kind in provided else "generated from the rotation pose")
        print(f"  {kind}: {n} frames x 8 directions ({source})")

    # per-direction anchors from the base pose, so every animation lines up
    info = {}
    for d, img in poses.items():
        x0, x1, top, bottom = bbox(img)
        ax, _ = feet_anchor(img)
        waist = top + int((bottom - top) * 0.55)
        info[d] = (ax, top, waist, bottom)

    def from_gifs(kind):
        """Align every frame of a direction with one shared anchor so the feet don't jitter."""
        per_dir, _ = gif_anims[kind]
        res = {}
        for d in DIRS:
            frames = per_dir[d]
            union = np.zeros_like(frames[0])
            for fr in frames:
                union[fr[:, :, 3] > 0] = fr[fr[:, :, 3] > 0]
            ax, bottom = feet_anchor(union)
            res[d] = [place(fr, ax, bottom) for fr in frames]
        return res

    def gif_fps(kind, default):
        if kind in fps_override:
            return fps_override[kind]
        return default

    def from_export(kind):
        res = {}
        for d in DIRS:
            ax, _, _, bottom = info[d]
            res[d] = [place(rgba(p), ax, bottom) for p in provided[kind][d]]
        return res

    # idle
    if "idle" in gif_anims:
        write("idle", from_gifs("idle"), gif_fps("idle", 6), True, source="from GIFs")
    elif "idle" in provided:
        write("idle", from_export("idle"), 6, True)
    else:
        idle = {}
        for d, img in poses.items():
            ax, top, waist, bottom = info[d]
            idle[d] = [place(breathe(img, top, waist, a), ax, bottom) for a in (0, 0, 1, 1)]
        write("idle", idle, 4, True)

    # walk
    if "walk" in gif_anims:
        write("walk", from_gifs("walk"), gif_fps("walk", 10), True, source="from GIFs")
    elif "walk" in provided:
        write("walk", from_export("walk"), 10, True)
    else:
        walk = {}
        for d, img in poses.items():
            ax, top, waist, bottom = info[d]
            walk[d] = [place(walk_frame(img, d, f / 8 * 2 * math.pi, top, waist, bottom, ax), ax, bottom)
                       for f in range(8)]
        write("walk", walk, 10, True)

    # attack
    if "attack" in gif_anims:
        n = len(gif_anims["attack"][0][DIRS[0]])
        write("attack", from_gifs("attack"), gif_fps("attack", 14), False, hit=max(0, n // 2), source="from GIFs")
    elif "attack" in provided:
        n = len(provided["attack"][DIRS[0]])
        write("attack", from_export("attack"), 14, False, hit=max(0, n // 2))
    else:
        attack = {}
        lunge = [0, -1, 2, 3, 2, 1]
        for d, img in poses.items():
            ax, top, waist, bottom = info[d]
            vx, vy = DIR_VEC[d]
            attack[d] = [place(img, ax, bottom, dx=int(round(vx * k)), dy=int(round(vy * k * 0.5))) for k in lunge]
        write("attack", attack, 16, False, hit=3)

    # any other animation passed with --anim (e.g. dodge, hurt, death): one-shot by default
    for kind in gif_anims:
        if kind not in ("idle", "walk", "attack"):
            write(kind, from_gifs(kind), gif_fps(kind, 12), False, source="from GIFs")

    meta_out = dict(frameWidth=FRAME, frameHeight=FRAME, pivotX=PIVOT[0], pivotY=PIVOT[1], ppu=64, animations=anims)
    with open(os.path.join(out_dir, "character.json"), "w") as fh:
        json.dump(meta_out, fh, indent=2)

    # portrait: head and shoulders of the south pose, scaled up 3x into 96x96
    if portrait_name:
        img = poses["south"]
        x0, x1, top, bottom = bbox(img)
        ax, _ = feet_anchor(img)
        size = 32
        cx = int(round(ax))
        crop = Image.fromarray(img).crop((cx - size // 2, top - 2, cx + size // 2, top - 2 + size))
        crop = crop.resize((96, 96), Image.NEAREST)
        os.makedirs(os.path.join(ART, "Portraits"), exist_ok=True)
        crop.save(os.path.join(ART, "Portraits", f"{portrait_name}.png"))
        print(f"  portrait: Portraits/{portrait_name}.png")

    # keep the source for reference (outside Assets, so Unity ignores it).
    # Stage everything in a temp dir first: the sources may themselves live in ArtSource/<name>/.
    keep = os.path.join(ROOT, "ArtSource", name)
    stage = tempfile.mkdtemp()
    shutil.copytree(folder, os.path.join(stage, "export"))
    for kind, pattern in (anim_files or {}).items():
        os.makedirs(os.path.join(stage, kind), exist_ok=True)
        for d in DIRS:
            src_path = os.path.expanduser(pattern.replace("{dir}", d))
            shutil.copy2(src_path, os.path.join(stage, kind, os.path.basename(src_path)))
    # anything from a previous import that wasn't re-supplied this time (e.g. old walk GIFs) is kept
    if os.path.exists(keep):
        for entry in os.listdir(keep):
            if not os.path.exists(os.path.join(stage, entry)) and entry not in os.listdir(os.path.join(stage, "export")):
                src_entry = os.path.join(keep, entry)
                dst_entry = os.path.join(stage, entry)
                (shutil.copytree if os.path.isdir(src_entry) else shutil.copy2)(src_entry, dst_entry)
        shutil.rmtree(keep)
    # flatten the export into the top level like before, extra animations as sub-folders
    shutil.copytree(os.path.join(stage, "export"), keep)
    for entry in os.listdir(stage):
        if entry != "export":
            src_entry = os.path.join(stage, entry)
            dst_entry = os.path.join(keep, entry)
            if not os.path.exists(dst_entry):
                (shutil.copytree if os.path.isdir(src_entry) else shutil.copy2)(src_entry, dst_entry)
    shutil.rmtree(stage)
    print(f"  source kept in ArtSource/{name}/")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("source", help="export .zip or folder containing rotations/<direction>.png")
    ap.add_argument("name", help="character folder name, e.g. warrior")
    ap.add_argument("--portrait", help="also write Art/Portraits/<name>.png")
    ap.add_argument("--anim", action="append", default=[], metavar="KIND=PATTERN",
                    help='e.g. walk="~/Downloads/hero_walking_{dir}.gif" (idle, walk, attack, dodge, or any name)')
    ap.add_argument("--fps", action="append", default=[], metavar="KIND=FPS", help="e.g. walk=10")
    a = ap.parse_args()
    anims = dict(x.split("=", 1) for x in a.anim)
    fps = {k: float(v) for k, v in (x.split("=", 1) for x in a.fps)}
    print(f"Importing {a.source} -> Art/Characters/{a.name}/")
    build(a.source, a.name, a.portrait, anims, fps)
