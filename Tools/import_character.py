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
    idle   = breathing (upper body bobs 1px), or the still pose with --static-idle
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
STATIC_IDLE = False # set by --static-idle: idle is the plain pose, no breathing
LEG_STRETCH = 0.0   # set by --leg-stretch: make legs this much longer (0.12 = 12%)
TORSO_STRETCH = 0.0 # set by --torso-stretch: make the torso (neck to hips) longer; the head is never stretched
THIGH_STRETCH = 0.0 # set by --thigh-stretch: extra stretch for the upper legs (hips to knees) only
HEAD_FRACTION = 0.2 # top 20% of the figure counts as the head
KNEE_FRACTION = 0.5 # knees sit halfway between hips and feet
STRETCH_KINDS = ("idle", "walk", "attack")  # not dodge: in a crouch/slide the "legs" rows contain the torso
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


def stretch_rows(img, y0, y1, factor):
    """Stretch rows [y0, y1) vertically by `factor` (nearest-neighbour, so pixels stay crisp).
    Returns the taller image and how many rows were added."""
    y0, y1 = max(0, int(y0)), min(img.shape[0], int(y1))
    if factor <= 0 or y1 <= y0:
        return img, 0
    n = y1 - y0
    new_n = int(round(n * (1 + factor)))
    idx = np.minimum((np.arange(new_n) * n / new_n).astype(int), n - 1)
    out = np.concatenate([img[:y0], img[y0:y1][idx], img[y1:]], axis=0)
    return out, new_n - n


def stretch_legs(img, hip_y, bottom, torso_len=0, extra_leg=0.0):
    """Apply TORSO_STRETCH to the torso (torso_len rows above the hips), THIGH_STRETCH to the upper legs
    and LEG_STRETCH (+ extra_leg) from the hips down to the feet. Rows below the feet are left alone.
    Returns the taller image and the new index of the bottom row."""
    added_total = 0
    if TORSO_STRETCH > 0 and torso_len > 0:
        img, added = stretch_rows(img, hip_y - torso_len, hip_y, TORSO_STRETCH)
        hip_y += added
        added_total += added
    if THIGH_STRETCH > 0:
        thigh = int(round((bottom + added_total - hip_y) * KNEE_FRACTION))
        img, added = stretch_rows(img, hip_y, hip_y + thigh, THIGH_STRETCH)
        added_total += added
    leg_factor = (1 + LEG_STRETCH) * (1 + extra_leg) - 1
    if leg_factor > 0:
        img, added = stretch_rows(img, hip_y, bottom + added_total + 1, leg_factor)
        added_total += added
    return img, bottom + added_total


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


def build(src, name, portrait_name, anim_files=None, fps_override=None, hit_override=None):
    folder = load_source(src)
    base, meta = find_metadata(folder)
    rotations = find_rotations(folder)
    if len(rotations) < 8:
        missing = [d for d in DIRS if d not in rotations]
        raise SystemExit(f"Missing directions: {missing}")
    poses = {d: rgba(p) for d, p in rotations.items()}
    provided = export_animations(base, meta)
    fps_override = fps_override or {}
    hit_override = hit_override or {}
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
    # hips sit at ~55% of the pose height; used to find the legs in every animation frame
    leg_len = {d: info[d][3] - info[d][2] for d in DIRS}
    # torso = from below the head down to the hips
    head_len = {d: int((info[d][3] - info[d][1]) * HEAD_FRACTION) for d in DIRS}
    torso_len = {d: info[d][2] - (info[d][1] + head_len[d]) for d in DIRS}
    # The rotation pose and the walk GIFs can be drawn at slightly different heights. Give the
    # animations built from the pose (idle, attack) extra leg length so they match the walk.
    pose_extra_leg = {d: 0.0 for d in DIRS}
    if "walk" in gif_anims and (LEG_STRETCH > 0 or TORSO_STRETCH > 0 or THIGH_STRETCH > 0):
        for d in DIRS:
            heights = []
            for fr in gif_anims["walk"][0][d]:
                ys = np.nonzero((fr[:, :, 3] > 0).any(axis=1))[0]
                heights.append(ys.max() - ys.min() + 1)
            diff = float(np.median(heights)) - (info[d][3] - info[d][1] + 1)
            if diff > 0:
                pose_extra_leg[d] = diff / max(1, leg_len[d])

    def placed(img, d, bottom, stretch, dx=0, dy=0, hip=None, extra_leg=0.0):
        """place() with the legs stretched first; hip defaults to the pose's leg length above `bottom`."""
        ax = info[d][0]
        if stretch and (LEG_STRETCH > 0 or TORSO_STRETCH > 0 or THIGH_STRETCH > 0):
            if hip is None:
                hip = bottom - leg_len[d]
            img, bottom = stretch_legs(img, hip, bottom, torso_len[d], extra_leg)
        return place(img, ax, bottom, dx, dy)

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
            if kind in STRETCH_KINDS and (LEG_STRETCH > 0 or TORSO_STRETCH > 0 or THIGH_STRETCH > 0):
                res[d] = []
                for fr in frames:
                    # measure from the top of this frame's figure, so the same body rows are
                    # stretched in every frame even while the body bobs (prevents flicker)
                    if kind == "attack":
                        # feet stay planted in a strike, and a raised sword would be mistaken for the head
                        hip = bottom - leg_len[d]
                    else:
                        top = np.nonzero((fr[:, :, 3] > 0).any(axis=1))[0].min()
                        hip = top + head_len[d] + torso_len[d]
                    tall, new_bottom = stretch_legs(fr, hip, bottom, torso_len[d])
                    res[d].append(place(tall, ax, new_bottom))
            else:
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
            res[d] = [placed(rgba(p), d, bottom, kind in STRETCH_KINDS) for p in provided[kind][d]]
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
            bobs = (0,) if STATIC_IDLE else (0, 0, 1, 1)  # breathing = upper body bobs 1px
            idle[d] = [placed(breathe(img, top, waist, a), d, bottom, True, hip=waist, extra_leg=pose_extra_leg[d])
                       for a in bobs]
        write("idle", idle, 4, True, source="still pose" if STATIC_IDLE else None)

    # walk
    if "walk" in gif_anims:
        write("walk", from_gifs("walk"), gif_fps("walk", 10), True, source="from GIFs")
    elif "walk" in provided:
        write("walk", from_export("walk"), 10, True)
    else:
        walk = {}
        for d, img in poses.items():
            ax, top, waist, bottom = info[d]
            walk[d] = [placed(walk_frame(img, d, f / 8 * 2 * math.pi, top, waist, bottom, ax), d, bottom, True, hip=waist,
                              extra_leg=pose_extra_leg[d])
                       for f in range(8)]
        write("walk", walk, 10, True)

    # attack
    if "attack" in gif_anims:
        n = len(gif_anims["attack"][0][DIRS[0]])
        hit = hit_override.get("attack", max(0, n // 2))
        write("attack", from_gifs("attack"), gif_fps("attack", 14), False, hit=hit, source=f"from GIFs, hit on frame {hit}")
    elif "attack" in provided:
        n = len(provided["attack"][DIRS[0]])
        write("attack", from_export("attack"), 14, False, hit=max(0, n // 2))
    else:
        attack = {}
        lunge = [0, -1, 2, 3, 2, 1]
        for d, img in poses.items():
            ax, top, waist, bottom = info[d]
            vx, vy = DIR_VEC[d]
            attack[d] = [placed(img, d, bottom, True, dx=int(round(vx * k)), dy=int(round(vy * k * 0.5)), hip=waist,
                                extra_leg=pose_extra_leg[d])
                         for k in lunge]
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
    ap.add_argument("--hit", action="append", default=[], metavar="KIND=FRAME",
                    help="frame (0-based) on which an attack deals damage, e.g. attack=6 (default: middle frame)")
    ap.add_argument("--leg-stretch", type=float, default=0.0,
                    help="make the legs longer in idle/walk/attack, e.g. 0.12 = 12%% (originals are not changed)")
    ap.add_argument("--torso-stretch", type=float, default=0.0,
                    help="make the torso (neck to hips) longer, e.g. 0.1 = 10%%; the head keeps its size")
    ap.add_argument("--thigh-stretch", type=float, default=0.0,
                    help="extra stretch for the upper legs only (hips to knees), e.g. 0.2 = 20%%")
    ap.add_argument("--static-idle", action="store_true",
                    help="idle is the still pose (no breathing); ignored if an idle animation is supplied")
    a = ap.parse_args()
    LEG_STRETCH = a.leg_stretch
    STATIC_IDLE = a.static_idle
    TORSO_STRETCH = a.torso_stretch
    THIGH_STRETCH = a.thigh_stretch
    anims = dict(x.split("=", 1) for x in a.anim)
    fps = {k: float(v) for k, v in (x.split("=", 1) for x in a.fps)}
    print(f"Importing {a.source} -> Art/Characters/{a.name}/")
    hits = {k: int(v) for k, v in (x.split("=", 1) for x in a.hit)}
    build(a.source, a.name, a.portrait, anims, fps, hits)
