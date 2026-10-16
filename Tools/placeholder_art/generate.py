#!/usr/bin/env python3
"""
Placeholder pixel-art generator for ActionRPG.

Builds tiny 3D "puppets" out of spheres/capsules, renders them from the game's isometric
camera angle (30 deg elevation = 2:1 tiles) and quantises the shading into a pixel-art look.
Everything it writes follows ART_SPEC.md, so any file can be replaced 1:1 by hand-made art.

Run:  Tools/.venv/bin/python Tools/placeholder_art/generate.py [characters|tiles|props|portraits]
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ART = os.path.join(ROOT, "Assets", "Resources", "Art")
PPU = 64

# Sheet row order (top to bottom) and the facing angle of each row (0 = east/right, 90 = north/up-screen)
DIRS = ["S", "SW", "W", "NW", "N", "NE", "E", "SE"]
DIR_ANGLE = {"S": 270, "SW": 225, "W": 180, "NW": 135, "N": 90, "NE": 45, "E": 0, "SE": 315}

SIN_E, COS_E = 0.5, math.sqrt(3) / 2  # camera elevation 30 deg
TO_CAM = np.array([0.0, -COS_E, SIN_E])
LIGHT = np.array([-0.5, -0.55, 0.7]) / np.linalg.norm([-0.5, -0.55, 0.7])

rng = np.random.default_rng(1234)


def unit(v):
    v = np.asarray(v, float)
    n = np.linalg.norm(v)
    return v / n if n > 1e-9 else v


def basis_from_z(n):
    n = unit(n)
    a = np.array([1.0, 0, 0]) if abs(n[0]) < 0.9 else np.array([0, 1.0, 0])
    u = unit(np.cross(a, n))
    v = np.cross(n, u)
    return np.stack([u, v, n], 1)


_fib = {}


def sphere_dirs(n):
    if n not in _fib:
        i = np.arange(n) + 0.5
        phi = np.arccos(1 - 2 * i / n)
        th = np.pi * (1 + 5 ** 0.5) * i
        _fib[n] = np.stack([np.cos(th) * np.sin(phi), np.sin(th) * np.sin(phi), np.cos(phi)], 1)
    return _fib[n]


# --------------------------------------------------------------------------------------------
# Point-cloud model + renderer
# --------------------------------------------------------------------------------------------
class Model:
    def __init__(self, density=1.0):
        self.P, self.N, self.C, self.E = [], [], [], []
        self.density = density

    def add(self, p, n, col, tex=0.06, emissive=False):
        p = np.asarray(p, float)
        col = np.broadcast_to(np.asarray(col, float), p.shape).copy()
        if tex:
            col *= 1 + tex * (rng.random((len(p), 1)) - 0.5) * 2
        self.P.append(p)
        self.N.append(n / np.linalg.norm(n, axis=1, keepdims=True))
        self.C.append(col)
        self.E.append(np.full(len(p), emissive))

    def ellipsoid(self, c, radii, col, basis=None, tex=0.06, jitter=0.0, bumps=0.0, emissive=False):
        radii = np.asarray(radii, float)
        area = 4 * math.pi * (radii[0] * radii[1] + radii[1] * radii[2] + radii[0] * radii[2]) / 3
        n = int(max(60, area * 9 * self.density))
        u = sphere_dirs(n)
        if bumps:
            ph = rng.random(6) * 10
            r = 1 + bumps * (np.sin(u[:, 0] * 5 + ph[0]) * np.sin(u[:, 1] * 4 + ph[1]) +
                             0.5 * np.sin(u[:, 2] * 7 + ph[2]) * np.sin(u[:, 0] * 6 + ph[3]))
            u = u * r[:, None]
        p = u * radii
        nrm = u / radii
        if jitter:
            nrm = unit_rows(nrm) + rng.normal(0, jitter, nrm.shape)
        if basis is not None:
            p = p @ basis.T
            nrm = nrm @ basis.T
        self.add(np.asarray(c) + p, nrm, col, tex, emissive)

    def sphere(self, c, r, col, **kw):
        self.ellipsoid(c, (r, r, r), col, **kw)

    def capsule(self, a, b, r, col, **kw):
        a, b = np.asarray(a, float), np.asarray(b, float)
        L = np.linalg.norm(b - a)
        k = max(2, int(L / (r * 0.5)) + 1)
        for t in np.linspace(0, 1, k):
            self.sphere(a + (b - a) * t, r, col, **kw)

    def cone(self, base, r, h, col, tex=0.06, jitter=0.0, stripes=0, stripe_col=None):
        base = np.asarray(base, float)
        n = int(max(200, math.pi * r * math.hypot(r, h) * 9 * self.density))
        t = np.sqrt(rng.random(n))  # uniform over the surface
        ang = rng.random(n) * 2 * math.pi
        rad = r * t
        p = base + np.stack([rad * np.cos(ang), rad * np.sin(ang), h * (1 - t)], 1)
        nrm = np.stack([np.cos(ang) * h, np.sin(ang) * h, np.full(n, r)], 1)
        if jitter:
            nrm = unit_rows(nrm) + rng.normal(0, jitter, nrm.shape)
        colors = np.broadcast_to(np.asarray(col, float), (n, 3)).copy()
        if stripes:
            mask = (np.floor(ang / (2 * math.pi) * stripes * 2) % 2) == 0
            colors[mask] = stripe_col
        self.add(p, nrm, colors, tex)

    def sheet(self, p00, p10, p01, p11, col, tex=0.06, steps=None):
        p00, p10, p01, p11 = (np.asarray(p, float) for p in (p00, p10, p01, p11))
        size = max(np.linalg.norm(p10 - p00), np.linalg.norm(p01 - p00), 1)
        k = steps or int(size * 3 * math.sqrt(self.density)) + 2
        u, v = np.meshgrid(np.linspace(0, 1, k), np.linspace(0, 1, k))
        u, v = u.ravel()[:, None], v.ravel()[:, None]
        p = (1 - u) * (1 - v) * p00 + u * (1 - v) * p10 + (1 - u) * v * p01 + u * v * p11
        nrm = np.cross(p10 - p00, p01 - p00)
        self.add(p, np.broadcast_to(nrm, p.shape).copy(), col, tex)

    def box(self, c, size, col, basis=None, tex=0.06, face_cols=None):
        """Axis-aligned (in `basis`) box; face_cols maps '+x','-x','+y','-y','+z' to colours."""
        c = np.asarray(c, float)
        B = basis if basis is not None else np.eye(3)
        hx, hy, hz = np.asarray(size, float) / 2
        faces = {
            "+x": ((hx, -hy, -hz), (hx, hy, -hz), (hx, -hy, hz), (hx, hy, hz)),
            "-x": ((-hx, -hy, -hz), (-hx, hy, -hz), (-hx, -hy, hz), (-hx, hy, hz)),
            "+y": ((-hx, hy, -hz), (hx, hy, -hz), (-hx, hy, hz), (hx, hy, hz)),
            "-y": ((-hx, -hy, -hz), (hx, -hy, -hz), (-hx, -hy, hz), (hx, -hy, hz)),
            "+z": ((-hx, -hy, hz), (hx, -hy, hz), (-hx, hy, hz), (hx, hy, hz)),
        }
        for name, corners in faces.items():
            pts = [c + B @ np.array(q) for q in corners]
            self.sheet(*pts, (face_cols or {}).get(name, col), tex)


def unit_rows(a):
    return a / np.linalg.norm(a, axis=1, keepdims=True)


def shift(a, dy, dx, fill):
    out = np.full_like(a, fill)
    H, W = a.shape[:2]
    ys, yd = (slice(0, H - dy), slice(dy, H)) if dy >= 0 else (slice(-dy, H), slice(0, H + dy))
    xs, xd = (slice(0, W - dx), slice(dx, W)) if dx >= 0 else (slice(-dx, W), slice(0, W + dx))
    out[yd, xd] = a[ys, xs]
    return out


def render(m, W, H, pivot, scale=1.0, outline=True, inner=True):
    """Render model to an RGBA image. pivot = pixel (from bottom-left) where world origin lands."""
    P = np.concatenate(m.P) * scale
    N = np.concatenate(m.N)
    C = np.concatenate(m.C)
    E = np.concatenate(m.E)
    sx = P[:, 0]
    sy = P[:, 2] * COS_E + P[:, 1] * SIN_E
    dep = P[:, 1] * COS_E - P[:, 2] * SIN_E
    px = np.floor(pivot[0] + sx).astype(np.int64)
    py = np.floor(pivot[1] + sy).astype(np.int64)
    ok = (px >= 0) & (px < W) & (py >= 0) & (py < H)
    px, py, dep, N, C, E = px[ok], py[ok], dep[ok], N[ok], C[ok], E[ok]
    idx = (H - 1 - py) * W + px

    z = np.full(W * H, np.inf)
    np.minimum.at(z, idx, dep)
    win = dep <= z[idx] + 1e-9

    N = np.where((N @ TO_CAM)[:, None] < 0, -N, N)
    lam = np.clip(N @ LIGHT, 0, 1)
    inten = 0.36 + 0.74 * lam
    q = np.select([inten < 0.55, inten < 0.78, inten < 0.97], [0.56, 0.75, 0.9], 1.05)
    q = np.where(E, 1.1, q)
    col = C * q[:, None]
    cool = np.array([0.86, 0.9, 1.12])
    warm = np.array([1.05, 1.02, 0.93])
    col = np.where((q < 0.6)[:, None], col * cool, np.where((q > 1)[:, None], col * warm, col))
    col = np.clip(col, 0, 255)

    img = np.zeros((W * H, 4))
    img[idx[win], :3] = col[win]
    img[idx[win], 3] = 255
    img = img.reshape(H, W, 4)
    zb = z.reshape(H, W)
    solid = img[:, :, 3] > 0

    if inner:
        # darken pixels sitting just behind a much nearer neighbour -> readable internal lines
        darker = np.zeros((H, W), bool)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nz = shift(zb, dy, dx, np.inf)
            darker |= solid & (nz < zb - 3.5)
        img[darker, :3] *= 0.72

    if outline:
        border = np.zeros((H, W), bool)
        acc = np.zeros((H, W, 3))
        cnt = np.zeros((H, W))
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ns = shift(solid, dy, dx, False)
            nc = shift(img[:, :, :3], dy, dx, 0)
            add = ~solid & ns
            border |= add
            acc[add] += nc[add]
            cnt[add] += 1
        out = acc[border] / cnt[border][:, None]
        img[border, :3] = out * 0.28 + np.array([12, 8, 16])
        img[border, 3] = 255

    return Image.fromarray(img.astype(np.uint8), "RGBA")


# --------------------------------------------------------------------------------------------
# Rig helper: local frame x = forward, y = left, z = up
# --------------------------------------------------------------------------------------------
class Rig:
    def __init__(self, m, angle_deg, origin=(0, 0, 0)):
        a = math.radians(angle_deg)
        self.m = m
        self.f = np.array([math.cos(a), math.sin(a), 0.0])
        self.l = np.array([-math.sin(a), math.cos(a), 0.0])
        self.u = np.array([0, 0, 1.0])
        self.o = np.asarray(origin, float)
        self.B = np.stack([self.f, self.l, self.u], 1)

    def w(self, p):
        p = np.asarray(p, float)
        return self.o + p[0] * self.f + p[1] * self.l + p[2] * self.u

    def v(self, d):
        d = np.asarray(d, float)
        return d[0] * self.f + d[1] * self.l + d[2] * self.u

    def ell(self, c, radii, col, **kw):
        self.m.ellipsoid(self.w(c), radii, col, basis=self.B, **kw)

    def sph(self, c, r, col, **kw):
        self.m.sphere(self.w(c), r, col, **kw)

    def cap(self, a, b, r, col, **kw):
        self.m.capsule(self.w(a), self.w(b), r, col, **kw)


V = lambda *a: np.array(a, float)

# --------------------------------------------------------------------------------------------
# Humanoids
# --------------------------------------------------------------------------------------------
STEEL = (165, 172, 185)
STEEL_LIGHT = (205, 212, 222)
LEATHER = (110, 72, 45)
DARK = (35, 28, 30)

LOOKS = {
    "warrior": dict(skin=(226, 176, 140), hair=(120, 80, 40), torso=STEEL, armor=True, skirt=(120, 125, 135),
                    belt=LEATHER, pants=(80, 70, 60), boots=(95, 62, 40), cape=(150, 30, 35), helmet=True,
                    plume=(185, 35, 40), shield=True, weapon="sword", arm=STEEL),
    "bandit": dict(skin=(205, 155, 120), torso=(95, 80, 55), skirt=(80, 66, 46), belt=(60, 40, 28),
                   pants=(70, 60, 48), boots=(60, 42, 30), hood=(62, 78, 52), weapon="dagger", arm=(95, 80, 55),
                   mask=(50, 40, 35)),
    "elder": dict(skin=(230, 190, 160), hair=(225, 225, 230), long_hair=True, robe=(80, 70, 140),
                  torso=(80, 70, 140), belt=(200, 170, 80), pants=(60, 55, 100), boots=(70, 50, 40),
                  weapon="staff", arm=(80, 70, 140), shawl=(120, 40, 60)),
    "merchant": dict(skin=(225, 172, 135), hair=(90, 60, 35), beard=(90, 60, 35), torso=(70, 120, 70),
                     skirt=(70, 120, 70), belt=LEATHER, pants=(110, 85, 60), boots=(80, 55, 38), hat=(150, 110, 60),
                     belly=True, build=1.15, arm=(70, 120, 70), apron=(210, 200, 170)),
    "guard": dict(skin=(215, 165, 130), hair=(50, 40, 35), beard=(50, 40, 35), torso=(140, 145, 155), armor=True,
                  skirt=(40, 60, 120), belt=LEATHER, pants=(60, 60, 70), boots=(70, 50, 38), helmet=True,
                  weapon="spear", arm=(140, 145, 155), tabard=(40, 60, 120)),
    "nomad": dict(skin=(170, 115, 80), robe=(220, 200, 160), torso=(220, 200, 160), belt=(150, 60, 40),
                  pants=(180, 160, 120), boots=(140, 100, 60), hood=(225, 210, 175), veil=(225, 210, 175),
                  arm=(220, 200, 160), shawl=(170, 70, 45)),
    "hunter": dict(skin=(232, 190, 165), hair=(210, 180, 110), beard=(210, 180, 110), torso=(115, 80, 55),
                   skirt=(105, 72, 50), belt=(70, 48, 30), pants=(90, 70, 55), boots=(80, 58, 40),
                   hood=(235, 235, 240), fur=(235, 235, 240), build=1.1, arm=(115, 80, 55), weapon="axe"),
}

# attack keyframes: (sweep angle deg from forward toward left, hand height offset, lean)
ATTACK_KEYS = [(-125, 15, 0.0), (-95, 14, 0.5), (-20, 11, 1.2), (45, 9.5, 1.4), (70, 8, 1.0), (30, 5, 0.4)]


def humanoid(m, L, angle, anim, t, frame=0):
    R = Rig(m, angle)
    ph = 2 * math.pi * t
    swing = bend_l = bend_r = breathe = lean = 0.0
    if anim == "walk":
        swing = 0.5 * math.sin(ph)
        bend_l = 0.8 * max(0.0, math.cos(ph))
        bend_r = 0.8 * max(0.0, -math.cos(ph))
    elif anim == "idle":
        breathe = 0.4 * math.sin(ph)
    atk = ATTACK_KEYS[frame] if anim == "attack" else None
    if atk:
        lean = atk[2]
        swing = [0, -0.15, 0.25, 0.35, 0.3, 0.1][frame]  # step into the swing

    thigh = shin = 10.0
    hz = 21 - 20 * (1 - math.cos(abs(swing))) * 0.9
    bw = L.get("build", 1.0)
    robe = L.get("robe")

    # legs
    for side, th, bd in ((1, swing, bend_l), (-1, -swing, bend_r)):
        hip = V(0, side * 2.4, hz)
        knee = hip + V(math.sin(th), 0, -math.cos(th)) * thigh
        ankle = knee + V(math.sin(th - bd), 0, -math.cos(th - bd)) * shin
        R.cap(hip, knee, 2.3, L["pants"])
        R.cap(knee, ankle, 2.0, L["boots"])
        R.ell(ankle + V(1.1, 0, -0.7), (2.7, 1.6, 1.3), L["boots"])

    # body
    if robe:
        R.ell(V(lean * 0.3, 0, (hz + 3) / 2), (4.4 * bw, 5.1 * bw, (hz + 3) / 2 + 0.8), robe, tex=0.08)
    else:
        R.ell(V(lean * 0.3, 0, hz - 1.2), (3.4 * bw, 4.4 * bw, 3.3), L["skirt"], tex=0.1)
    if L.get("apron"):
        R.ell(V(1.4 + lean * 0.3, 0, hz + 1), (2.4 * bw, 3.4 * bw, 5), L["apron"])
    R.ell(V(lean * 0.6, 0, hz + 7.5 + breathe * 0.3), (3.0 * bw, 4.6 * bw, 6.4), L["torso"], tex=0.07)
    if L.get("belly"):
        R.ell(V(1.4 + lean * 0.5, 0, hz + 4.5), (3.6, 4.5 * bw, 3.8), L["torso"])
    if L.get("tabard"):
        R.ell(V(1.0 + lean * 0.5, 0, hz + 5), (2.4, 3.0, 6.5), L["tabard"])
    R.ell(V(lean * 0.5, 0, hz + 1.6), (3.3 * bw, 4.4 * bw, 1.0), L["belt"])
    if L.get("fur"):
        R.ell(V(lean, 0, hz + 12.2), (4.2 * bw, 6.2 * bw, 2.0), L["fur"], tex=0.15, jitter=0.3)
    if L.get("shawl"):
        R.ell(V(lean, 0, hz + 12.0), (3.8 * bw, 5.6 * bw, 1.6), L["shawl"])

    # cape (behind the body)
    if L.get("cape"):
        sway = 1.5 * abs(swing) + (1.5 if atk else 0)
        R_top = [R.w(V(-3.2 + lean * 0.6, s * 4.4, hz + 12.5)) for s in (1, -1)]
        R_bot = [R.w(V(-5.2 - sway, s * 6.0, hz - 8)) for s in (1, -1)]
        m.sheet(R_top[0], R_top[1], R_bot[0], R_bot[1], L["cape"], tex=0.08)

    # head
    hc = V(lean + 0.3, 0, hz + 18 + breathe * 0.2)
    R.cap(V(lean, 0, hz + 13), V(lean, 0, hz + 15.5), 1.4, L["skin"])
    R.sph(hc, 3.3, L["skin"], tex=0.03)
    for s in (1, -1):
        R.sph(hc + V(2.85, s * 1.15, 0.4), 0.5, DARK, tex=0)
    if L.get("helmet"):
        R.ell(hc + V(-0.2, 0, 1.0), (3.75, 3.8, 3.25), STEEL, tex=0.04)
        R.cap(hc + V(3.4, 0, 2.3), hc + V(3.6, 0, -0.6), 0.55, STEEL)
        if L.get("plume"):
            R.cap(hc + V(2.0, 0, 4.1), hc + V(-2.5, 0, 4.4), 1.1, L["plume"], tex=0.12)
            R.cap(hc + V(-2.5, 0, 4.4), hc + V(-5.0, 0, 1.0), 0.9, L["plume"], tex=0.12)
    elif L.get("hood"):
        R.ell(hc + V(-0.8, 0, 0.6), (3.9, 4.05, 3.95), L["hood"], tex=0.08)
    elif L.get("hair"):
        R.ell(hc + V(-0.7, 0, 0.9), (3.4, 3.55, 3.0), L["hair"], tex=0.1)
        if L.get("long_hair"):
            R.ell(hc + V(-1.7, 0, -2.6), (2.2, 3.2, 3.6), L["hair"], tex=0.1)
    if L.get("hat"):
        R.ell(hc + V(0, 0, 2.6), (5.6, 5.6, 0.6), L["hat"])
        R.ell(hc + V(-0.2, 0, 3.9), (3.2, 3.2, 2.0), L["hat"])
    if L.get("beard"):
        R.ell(hc + V(2.0, 0, -2.0), (1.9, 2.6, 2.0), L["beard"], tex=0.12)
    if L.get("veil") or L.get("mask"):
        R.ell(hc + V(1.7, 0, -1.3), (1.9, 3.0, 1.6), L.get("veil") or L.get("mask"))

    # arms
    sh_z = hz + 12
    if atk:
        beta = math.radians(atk[0])
        hand_r = V(0.5 + 6.5 * math.cos(beta), -1 + 6.5 * math.sin(beta), hz + atk[1])
        blade = unit(V(math.cos(beta), math.sin(beta), 0.25 - 0.06 * frame))
    else:
        hand_r = V(2.2 + 5 * swing, -5.7, hz + 3 + breathe * 0.2)
        blade = unit(V(0.75, -0.12, -0.65))
    if L.get("shield"):
        hand_l = V(2.8 - 2 * swing, 5.4, hz + 4.5)
    else:
        hand_l = V(0.8 - 5 * swing, 5.8, hz + 2.6 + breathe * 0.2)
    weapon = L.get("weapon")
    if weapon in ("staff", "spear") and not atk:
        hand_r = V(2.6 + 2 * swing, -5.6, hz + 6)

    for side, hand in ((-1, hand_r), (1, hand_l)):
        s = V(lean * 0.6, side * 5.3 * bw, sh_z)
        elbow = (s + hand) / 2 + V(-0.8, side * 1.2, -1.0)
        if L.get("armor"):
            R.sph(s + V(-0.2, side * 0.2, 0.6), 2.5, L["torso"], tex=0.04)
        R.cap(s, elbow, 1.7, L["arm"])
        R.cap(elbow, hand, 1.5, L["arm"] if not robe else L["arm"])
        R.sph(hand, 1.35, L["skin"] if not L.get("armor") else STEEL)

    # weapon in right hand
    if weapon == "sword" or weapon == "dagger":
        length = 16 if weapon == "sword" else 7
        d = blade
        perp = unit(np.cross(R.v(d), [0, 0, 1])) if abs(R.v(d)[2]) < 0.95 else R.l
        R.cap(hand_r - d * 1.6, hand_r + d * 1.2, 0.7, LEATHER)
        gw = R.w(hand_r + d * 1.4)
        m.capsule(gw - perp * 2.4, gw + perp * 2.4, 0.6, (190, 160, 80))
        R.cap(hand_r + d * 1.6, hand_r + d * length, 0.75, STEEL_LIGHT, tex=0.02)
        R.sph(hand_r - d * 1.9, 0.8, (190, 160, 80))
    elif weapon == "axe":
        d = blade if atk else unit(V(0.3, 0, -1))
        R.cap(hand_r - d * 2, hand_r + d * 10, 0.7, LEATHER)
        R.ell(hand_r + d * 9.5 + V(0, 0, 0) + R.l * 0, (2.6, 0.6, 2.2), STEEL_LIGHT)
    elif weapon == "staff":
        R.cap(hand_r + V(0, 0, -16), hand_r + V(0, 0, 14), 0.85, (120, 85, 50))
        R.sph(hand_r + V(0, 0, 15.5), 1.7, (120, 220, 255), emissive=True, tex=0)
    elif weapon == "spear":
        d = unit(V(0.15, 0, 1))
        R.cap(hand_r - d * 14, hand_r + d * 20, 0.65, (120, 85, 50))
        R.cap(hand_r + d * 20, hand_r + d * 24, 0.9, STEEL_LIGHT)

    # shield on left forearm
    if L.get("shield"):
        n = unit(R.v(V(0.5, 0.85, 0)))
        c = R.w(hand_l + V(0.4, 1.7, 1.5))
        B = basis_from_z(n)
        m.ellipsoid(c - n * 0.3, (6.1, 6.1, 0.7), STEEL, basis=B)
        m.ellipsoid(c, (5.5, 5.5, 0.9), (125, 80, 45), basis=B, tex=0.1)
        m.sphere(c + n * 0.9, 1.2, STEEL_LIGHT)


# --------------------------------------------------------------------------------------------
# Creatures
# --------------------------------------------------------------------------------------------
def wolf(m, angle, anim, t, frame=0, fur=(115, 108, 100), belly=(170, 160, 145)):
    R = Rig(m, angle)
    ph = 2 * math.pi * t
    s = 0.5 * math.sin(ph) if anim == "walk" else 0.0
    bob = 0.6 * abs(math.sin(ph)) if anim == "walk" else 0.3 * math.sin(ph)
    lunge = 0.0
    head_dip = 0.0
    if anim == "attack":
        k = [0, -0.4, 1.0, 1.6, 0.9, 0.3][frame]
        lunge, head_dip = 4 * k, 1.5 * k
    o = V(lunge, 0, bob)
    R.ell(o + V(0, 0, 10), (9, 3.8, 4.2), fur, tex=0.12, jitter=0.2)
    R.ell(o + V(0, 0, 8.6), (7, 3.2, 2.6), belly, tex=0.1)
    R.sph(o + V(5, 0, 10.8), 4.7, fur, tex=0.12, jitter=0.2)
    hc = o + V(11.5, 0, 13.5 - head_dip)
    R.ell(hc, (3.6, 3.0, 3.0), fur, tex=0.1)
    R.ell(hc + V(3.5, 0, -1.0), (2.5, 1.45, 1.35), belly)
    R.sph(hc + V(5.8, 0, -0.7), 0.7, DARK, tex=0)
    for side in (1, -1):
        R.cap(hc + V(-1, side * 1.6, 2.4), hc + V(-1.6, side * 1.9, 5.0), 0.85, fur)
        R.sph(hc + V(2.5, side * 1.4, 0.8), 0.45, (230, 200, 60), tex=0, emissive=True)
    R.cap(o + V(-8.5, 0, 11), o + V(-14, 0, 9.5 + bob), 1.7, fur, tex=0.12)
    R.cap(o + V(-14, 0, 9.5 + bob), o + V(-17.5, 0, 8), 1.2, belly)
    for fx, ph_sign in ((6.0, 1), (-6.0, -1)):
        for side in (1, -1):
            a = s * ph_sign * side
            hip = o + V(fx, side * 2.4, 9)
            knee = hip + V(math.sin(a) * 4.5, 0, -4.5)
            foot = V(hip[0] + math.sin(a) * 8.5, side * 2.5, 0.8)
            R.cap(hip, knee, 1.4, fur)
            R.cap(knee, foot, 1.0, fur)


def scorpion(m, angle, anim, t, frame=0, shell=(185, 125, 60), dark=(120, 70, 35)):
    R = Rig(m, angle)
    ph = 2 * math.pi * t
    strike = [0, -0.3, 0.6, 1.0, 0.7, 0.2][frame] if anim == "attack" else 0.0
    R.ell(V(0, 0, 4), (6.5, 4.5, 2.6), shell, tex=0.08)
    R.ell(V(6, 0, 4.2), (3.2, 3.8, 2.1), shell, tex=0.08)
    for side in (1, -1):
        R.sph(V(8.6, side * 1.4, 5.4), 0.5, DARK, tex=0)
        claw_open = 0.6 + 0.4 * math.sin(ph * 2)
        R.cap(V(7, side * 3, 4), V(11, side * 6, 4.8), 1.2, dark)
        R.ell(V(13.4, side * 6.4, 4.8), (2.5, 1.6, 1.3), shell)
        R.cap(V(14.5, side * (6.4 - claw_open), 4.8), V(16.5, side * (6.0 - claw_open * 1.5), 4.8), 0.6, dark)
        for i, lx in enumerate((3.5, 1.2, -1.2, -3.5)):
            a = 0.35 * math.sin(ph + i * 1.6 + (0 if side > 0 else math.pi)) if anim == "walk" else 0
            R.cap(V(lx, side * 3.8, 4), V(lx + a * 3, side * 7.5, 5), 0.7, dark)
            R.cap(V(lx + a * 3, side * 7.5, 5), V(lx + a * 4, side * 9.5, 0.5), 0.6, dark)
    rest = [V(-6, 0, 4.5), V(-10, 0, 7), V(-11.5, 0, 11), V(-10.5, 0, 15), V(-7.5, 0, 17.5), V(-4, 0, 18)]
    hit = [V(-6, 0, 4.5), V(-8, 0, 9), V(-6, 0, 14), V(-1, 0, 16), V(4, 0, 13), V(8, 0, 9)]
    pts = [r + (h - r) * strike for r, h in zip(rest, hit)]
    for i, p in enumerate(pts):
        R.sph(p, 2.1 - i * 0.15, shell if i % 2 else dark, tex=0.08)
    tip = pts[-1] + unit(pts[-1] - pts[-2]) * 3
    R.cap(pts[-1], tip, 0.7, DARK)


# --------------------------------------------------------------------------------------------
# Character sheets
# --------------------------------------------------------------------------------------------
FRAME = 64
PIVOT = (32, 10)
ANIMS = {
    "idle": dict(frames=4, fps=5, loop=True),
    "walk": dict(frames=8, fps=12, loop=True),
    "attack": dict(frames=6, fps=16, loop=False, hitFrame=3),
}

CHARACTERS = {
    "warrior": (lambda m, a, an, t, f: humanoid(m, LOOKS["warrior"], a, an, t, f), ["idle", "walk", "attack"]),
    "bandit": (lambda m, a, an, t, f: humanoid(m, LOOKS["bandit"], a, an, t, f), ["idle", "walk", "attack"]),
    "elder": (lambda m, a, an, t, f: humanoid(m, LOOKS["elder"], a, an, t, f), ["idle", "walk"]),
    "merchant": (lambda m, a, an, t, f: humanoid(m, LOOKS["merchant"], a, an, t, f), ["idle", "walk"]),
    "guard": (lambda m, a, an, t, f: humanoid(m, LOOKS["guard"], a, an, t, f), ["idle", "walk"]),
    "nomad": (lambda m, a, an, t, f: humanoid(m, LOOKS["nomad"], a, an, t, f), ["idle", "walk"]),
    "hunter": (lambda m, a, an, t, f: humanoid(m, LOOKS["hunter"], a, an, t, f), ["idle", "walk"]),
    "wolf": (lambda m, a, an, t, f: wolf(m, a, an, t, f), ["idle", "walk", "attack"]),
    "frost_wolf": (lambda m, a, an, t, f: wolf(m, a, an, t, f, fur=(205, 212, 225), belly=(240, 242, 248)),
                   ["idle", "walk", "attack"]),
    "scorpion": (lambda m, a, an, t, f: scorpion(m, a, an, t, f), ["idle", "walk", "attack"]),
}


def build_character(name):
    fn, anims = CHARACTERS[name]
    out = os.path.join(ART, "Characters", name)
    os.makedirs(out, exist_ok=True)
    meta = dict(frameWidth=FRAME, frameHeight=FRAME, pivotX=PIVOT[0], pivotY=PIVOT[1], ppu=PPU, animations=[])
    for anim in anims:
        spec = ANIMS[anim]
        n = spec["frames"]
        sheet = Image.new("RGBA", (FRAME * n, FRAME * len(DIRS)))
        for row, d in enumerate(DIRS):
            for f in range(n):
                m = Model()
                fn(m, DIR_ANGLE[d], anim, f / n, f)
                sheet.paste(render(m, FRAME, FRAME, PIVOT), (f * FRAME, row * FRAME))
        sheet.save(os.path.join(out, f"{anim}.png"))
        entry = dict(name=anim, file=anim, frames=n, fps=spec["fps"], loop=spec["loop"])
        entry["hitFrame"] = spec.get("hitFrame", -1)
        meta["animations"].append(entry)
    with open(os.path.join(out, "character.json"), "w") as fh:
        json.dump(meta, fh, indent=2)
    print("character", name)


def build_portraits():
    out = os.path.join(ART, "Portraits")
    os.makedirs(out, exist_ok=True)
    for name in ["warrior", "bandit", "elder", "merchant", "guard", "nomad", "hunter"]:
        m = Model(density=10)
        humanoid(m, LOOKS[name], 252, "idle", 0.25)
        img = render(m, 96, 96, (48, 52 - 39.5 * COS_E * 3), scale=3)
        img.save(os.path.join(out, f"{name}.png"))
        print("portrait", name)


# --------------------------------------------------------------------------------------------
# Props (static, one image each)
# --------------------------------------------------------------------------------------------
GROUND_CELL_X = V(32, 32, 0)   # one cell step along grid x, in ground pixels
GROUND_CELL_Y = V(-32, 32, 0)


def prop_oak(m):
    m.capsule(V(0, 0, 0), V(0, 0, 30), 2.6, (95, 65, 42), tex=0.12)
    for a in (0, 2.1, 4.2):
        m.capsule(V(0, 0, 2), V(math.cos(a) * 4.5, math.sin(a) * 4.5, 0), 1.6, (95, 65, 42))
    m.capsule(V(0, 0, 26), V(-7, 3, 38), 1.6, (95, 65, 42))
    m.capsule(V(0, 0, 26), V(7, -2, 40), 1.6, (95, 65, 42))
    greens = [(70, 120, 50), (60, 105, 45), (85, 135, 55)]
    for i in range(16):
        d = rng.normal(0, 1, 3) * V(9, 9, 6)
        r = rng.uniform(7, 10)
        m.sphere(V(0, 0, 48) + d, r, greens[i % 3], tex=0.25, jitter=0.45)


def prop_pine(m, snow=False):
    m.capsule(V(0, 0, 0), V(0, 0, 14), 2.2, (90, 60, 40), tex=0.12)
    tiers = [(17, 12, 22), (14, 26, 20), (10.5, 39, 17), (7, 51, 14), (3.5, 61, 10)]
    for r, z, h in tiers:
        p0 = len(m.P)
        m.cone(V(0, 0, z), r, h, (40, 85, 50), tex=0.2, jitter=0.4)
        if snow:
            N, C = m.N[p0], m.C[p0]
            top = N[:, 2] > 0.55
            C[top] = np.array([235, 240, 250]) * (1 + 0.05 * (rng.random((top.sum(), 1)) - 0.5))


def prop_bush(m):
    for i in range(7):
        d = rng.normal(0, 1, 3) * V(4, 4, 2)
        m.sphere(V(0, 0, 6) + d, rng.uniform(3.5, 5.5), (65, 110, 45), tex=0.25, jitter=0.45)
    for i in range(5):
        d = rng.normal(0, 1, 3) * V(4, 4, 2.5)
        m.sphere(V(0, 0, 8) + d, 0.9, (200, 40, 50), tex=0)  # berries


def prop_rock(m, col=(130, 128, 125), cap=None):
    p0 = len(m.P)
    m.ellipsoid(V(0, 0, 3.5), (9, 7, 6), col, tex=0.12, bumps=0.12)
    m.ellipsoid(V(5, -4, 2), (4, 3.5, 3), col, tex=0.12, bumps=0.15)
    if cap:
        for k in range(p0, len(m.P)):
            top = m.N[k][:, 2] > 0.5
            m.C[k][top] = cap


def prop_cactus(m):
    def ribbed(a, b, r):
        p0 = len(m.P)
        m.capsule(a, b, r, (70, 130, 70), tex=0.06)
        for k in range(p0, len(m.P)):
            ang = np.arctan2(m.N[k][:, 1], m.N[k][:, 0])
            m.C[k] *= (0.85 + 0.15 * np.cos(ang * 8))[:, None]
    ribbed(V(0, 0, 0), V(0, 0, 36), 3.4)
    ribbed(V(0, 2, 14), V(0, 8, 16), 2.3)
    ribbed(V(0, 8, 16), V(0, 8, 27), 2.3)
    ribbed(V(0, -2, 19), V(0, -7, 21), 2.0)
    ribbed(V(0, -7, 21), V(0, -7, 29), 2.0)


def prop_palm(m):
    pts = [V(0, 0, 0), V(2, 0, 14), V(5, 0, 28), V(9, 0, 40), V(12, 0, 50)]
    for a, b in zip(pts, pts[1:]):
        p0 = len(m.P)
        m.capsule(a, b, 2.6, (140, 105, 70), tex=0.1)
        for k in range(p0, len(m.P)):
            m.C[k] *= (0.85 + 0.15 * np.sign(np.sin(m.P[k][:, 2] * 1.2)))[:, None]
    top = pts[-1]
    for i in range(8):
        a = i * math.pi / 4 + 0.2
        d = V(math.cos(a), math.sin(a), 0)
        mid = top + d * 9 + V(0, 0, 2)
        end = top + d * 18 + V(0, 0, -6)
        B = basis_from_z(unit(np.cross(d, [0, 0, 1])) * 0.3 + V(0, 0, 1))
        m.ellipsoid((top + mid) / 2, (5, 2.2, 0.6), (70, 125, 50), basis=B, tex=0.2, jitter=0.3)
        m.ellipsoid((mid + end) / 2, (5, 1.8, 0.6), (60, 110, 45), basis=B, tex=0.2, jitter=0.3)
    for i in range(3):
        m.sphere(top + V(math.cos(i * 2.1) * 1.8, math.sin(i * 2.1) * 1.8, -1.5), 1.3, (110, 75, 40))


def prop_house(m):
    ex, ey = unit(GROUND_CELL_X), unit(GROUND_CELL_Y)
    B = np.stack([ex, ey, V(0, 0, 1)], 1)
    side = np.linalg.norm(GROUND_CELL_X) * 2 * 0.9  # 2x2 cells, slight inset
    wall_h = 34
    m.box(V(0, 0, wall_h / 2), (side, side, wall_h), (225, 210, 180), basis=B, tex=0.06)
    # timber frame
    for sx in (-1, 1):
        for sy in (-1, 1):
            c = ex * sx * side / 2 + ey * sy * side / 2
            m.capsule(c, c + V(0, 0, wall_h), 1.4, (100, 70, 45))
    for face_n, face_t in ((-ey, ex), (-ex, ey)):
        base = face_n * (side / 2 + 0.3)
        m.capsule(base - face_t * side / 2 + V(0, 0, wall_h), base + face_t * side / 2 + V(0, 0, wall_h), 1.3, (100, 70, 45))
        m.capsule(base - face_t * side / 2 + V(0, 0, 14), base + face_t * side / 2 + V(0, 0, 14), 1.0, (100, 70, 45))
    # door on the front-right face, window on the front-left face
    door_c = -ey * (side / 2 + 0.6) + V(0, 0, 9)
    m.box(door_c, (12, 1.2, 18), (90, 60, 40), basis=B, tex=0.1)
    m.sphere(door_c + -ey * 0.8 + ex * 3.5 + V(0, 0, -1), 0.8, (200, 170, 90))
    win_c = -ex * (side / 2 + 0.6) + V(0, 0, 21)
    m.box(win_c, (1.2, 10, 8), (60, 80, 110), basis=B, tex=0.05)
    # gable roof along ey
    ridge_h = wall_h + 26
    over = 5
    hs = side / 2 + over
    for sgn in (-1, 1):
        p00 = ey * -hs + ex * sgn * hs + V(0, 0, wall_h - 3)
        p10 = ey * hs + ex * sgn * hs + V(0, 0, wall_h - 3)
        p01 = ey * -hs + V(0, 0, ridge_h)
        p11 = ey * hs + V(0, 0, ridge_h)
        p0 = len(m.P)
        m.sheet(p00, p10, p01, p11, (165, 75, 55), tex=0.1)
        k = p0
        rows = np.dot(m.P[k] - V(0, 0, wall_h - 3), V(0, 0, 1))
        m.C[k] *= (0.85 + 0.15 * (np.floor(rows / 3) % 2))[:, None]
    for sgn in (-1, 1):  # gable ends
        a = ey * sgn * (side / 2) + ex * -side / 2 + V(0, 0, wall_h)
        b = ey * sgn * (side / 2) + ex * side / 2 + V(0, 0, wall_h)
        c = ey * sgn * (side / 2) + V(0, 0, ridge_h - 2)
        m.sheet(a, b, (a + c) / 2 + (c - a) / 2, c, (215, 200, 170), tex=0.06)
    m.box(ex * 8 + ey * 6 + V(0, 0, ridge_h + 2), (6, 6, 14), (120, 110, 105), basis=B, tex=0.1)


def prop_tent(m):
    m.cone(V(0, 0, 0), 24, 30, (200, 170, 120), tex=0.08, stripes=6, stripe_col=(170, 70, 50))
    m.capsule(V(0, 0, 28), V(0, 0, 36), 0.8, (110, 80, 50))


def prop_campfire(m):
    for a in (0, 1.2, 2.4):
        d = V(math.cos(a), math.sin(a), 0) * 6
        m.capsule(-d + V(0, 0, 1.2), d + V(0, 0, 1.2), 1.3, (100, 65, 40))
    for i in range(8):
        a = i * math.pi / 4
        m.sphere(V(math.cos(a) * 8, math.sin(a) * 8, 1), 1.8, (120, 118, 115), tex=0.15, bumps=0.2)
    m.ellipsoid(V(0, 0, 5), (3.5, 3.5, 5), (255, 150, 40), emissive=True, tex=0.15)
    m.ellipsoid(V(0, 0, 4.5), (2, 2, 3.5), (255, 230, 120), emissive=True, tex=0.1)


def prop_well(m):
    for i in range(16):
        a = i * math.pi / 8
        m.box(V(math.cos(a) * 9, math.sin(a) * 9, 4), (4, 4, 8), (135, 130, 125), tex=0.15)
    m.ellipsoid(V(0, 0, 7.5), (7.5, 7.5, 0.3), (40, 70, 100), tex=0.1)
    for s in (-1, 1):
        m.capsule(V(s * 9, 0, 8), V(s * 9, 0, 26), 1.2, (100, 70, 45))
    for s in (-1, 1):
        m.sheet(V(-12, s * 8, 22), V(12, s * 8, 22), V(-12, 0, 30), V(12, 0, 30), (150, 70, 50))


# name: (builder, frame w, frame h, pivot, collider, fade-when-behind)
PROPS = {
    "tree_oak": (prop_oak, 96, 112, (48, 14), dict(type="ellipse", radius=0.18), True),
    "tree_pine": (lambda m: prop_pine(m), 80, 112, (40, 14), dict(type="ellipse", radius=0.16), True),
    "tree_pine_snow": (lambda m: prop_pine(m, True), 80, 112, (40, 14), dict(type="ellipse", radius=0.16), True),
    "bush": (prop_bush, 48, 40, (24, 12), dict(type="ellipse", radius=0.14), False),
    "rock": (lambda m: prop_rock(m), 48, 40, (24, 12), dict(type="ellipse", radius=0.18), False),
    "rock_snow": (lambda m: prop_rock(m, (125, 130, 140), (235, 240, 250)), 48, 40, (24, 12),
                  dict(type="ellipse", radius=0.18), False),
    "rock_sand": (lambda m: prop_rock(m, (185, 140, 95)), 48, 40, (24, 12), dict(type="ellipse", radius=0.18), False),
    "cactus": (prop_cactus, 48, 72, (24, 12), dict(type="ellipse", radius=0.1), True),
    "palm": (prop_palm, 96, 112, (40, 14), dict(type="ellipse", radius=0.12), True),
    "house": (prop_house, 144, 150, (72, 38), dict(type="diamond", halfWidth=0.9, halfHeight=0.45), True),
    "tent": (prop_tent, 64, 64, (32, 16), dict(type="diamond", halfWidth=0.4, halfHeight=0.2), True),
    "campfire": (prop_campfire, 40, 32, (20, 12), dict(type="ellipse", radius=0.12), False),
    "well": (prop_well, 48, 56, (24, 14), dict(type="ellipse", radius=0.2), False),
}


def build_props():
    out = os.path.join(ART, "Props")
    os.makedirs(out, exist_ok=True)
    meta = {}
    for name, (fn, w, h, pivot, collider, fade) in PROPS.items():
        m = Model()
        fn(m)
        render(m, w, h, pivot).save(os.path.join(out, f"{name}.png"))
        meta[name] = dict(pivotX=pivot[0], pivotY=pivot[1], collider=collider, fade=fade)
        print("prop", name)
    # JsonUtility can't read dictionaries, so store as a list
    entries = [dict(name=k, **v) for k, v in meta.items()]
    for e in entries:
        c = e.pop("collider")
        e["colliderType"] = c["type"]
        e["radius"] = c.get("radius", 0)
        e["halfWidth"] = c.get("halfWidth", 0)
        e["halfHeight"] = c.get("halfHeight", 0)
        # multi-cell props are anchored on the corner shared by their cells
        e["offsetX"] = e["offsetY"] = 0.5 if e["name"] == "house" else 0.0
    with open(os.path.join(out, "props.json"), "w") as fh:
        json.dump(dict(props=entries), fh, indent=2)


# --------------------------------------------------------------------------------------------
# Ground tiles: 64x32 diamonds, seamless (noise is periodic in tile space), N variants side by side
# --------------------------------------------------------------------------------------------
TW, TH = 64, 32


def tile_coords():
    y, x = np.mgrid[0:TH, 0:TW]
    dx = x + 0.5 - TW / 2
    dy = TH / 2 - (y + 0.5)
    inside = np.abs(dx) / (TW / 2) + np.abs(dy) / (TH / 2) <= 1
    a = (dx / 32 + dy / 16) / 2 + 0.5
    b = (dy / 16 - dx / 32) / 2 + 0.5
    return a % 1, b % 1, inside


def pnoise(a, b, freq, seed):
    g = np.random.default_rng(seed).random((freq, freq))
    fa, fb = a * freq, b * freq
    i0, j0 = np.floor(fa).astype(int) % freq, np.floor(fb).astype(int) % freq
    i1, j1 = (i0 + 1) % freq, (j0 + 1) % freq
    ta, tb = fa - np.floor(fa), fb - np.floor(fb)
    ta, tb = ta * ta * (3 - 2 * ta), tb * tb * (3 - 2 * tb)
    top = g[i0, j0] * (1 - ta) + g[i1, j0] * ta
    bot = g[i0, j1] * (1 - ta) + g[i1, j1] * ta
    return top * (1 - tb) + bot * tb


def fbm(a, b, seed, variant, octaves=(4, 8, 16, 32)):
    total, amp, norm = 0, 1.0, 0
    for k, f in enumerate(octaves):
        s = seed * 100 + k + (variant * 17 if f >= 16 else 0)  # low octaves shared -> seams invisible
        total = total + amp * pnoise(a, b, f, s)
        norm += amp
        amp *= 0.55
    return total / norm


def voronoi_edges(a, b, seed, n=6):
    pts = np.random.default_rng(seed).random((n, 2))
    d = []
    for p in pts:
        for ox in (-1, 0, 1):
            for oy in (-1, 0, 1):
                d.append(np.hypot(a - p[0] - ox, b - p[1] - oy))
    d = np.sort(np.stack(d), axis=0)
    return d[1] - d[0]


def palette(dark, light, n=6):
    dark, light = np.array(dark, float), np.array(light, float)
    return [dark + (light - dark) * i / (n - 1) for i in range(n)]


def quant(v, pal):
    idx = np.clip((v * len(pal)).astype(int), 0, len(pal) - 1)
    return np.array(pal)[idx]


def tile_img(rgb, inside):
    img = np.zeros((TH, TW, 4), np.uint8)
    img[..., :3] = np.clip(rgb, 0, 255)
    img[..., 3] = inside * 255
    return img


def t_grass(v, a, b, inside, r, base=((40, 70, 35), (120, 165, 70)), flowers=False, litter=False):
    n = fbm(a, b, 1, v)
    val = 0.65 * n + 0.35 * r.random(n.shape)
    rgb = quant(val, palette(*base))
    blades = r.random(n.shape) < 0.07
    rgb[blades] = rgb[blades] * 1.18
    rgb[np.roll(blades, 1, 0)] *= 0.85
    if litter:
        leaves = (r.random(n.shape) < 0.05) & (pnoise(a, b, 8, 9 + v) > 0.45)
        rgb[leaves] = np.array([[130, 90, 45], [150, 105, 50], [110, 70, 40]])[r.integers(0, 3, leaves.sum())]
    if flowers:
        f = r.random(n.shape) < 0.012
        cols = np.array([[240, 240, 235], [245, 210, 70], [230, 120, 160], [140, 160, 240]])
        rgb[f] = cols[r.integers(0, 4, f.sum())]
    return rgb


def t_path(v, a, b, inside, r):
    n = fbm(a, b, 2, v)
    rgb = quant(0.7 * n + 0.3 * r.random(n.shape), palette((95, 72, 50), (165, 135, 95)))
    peb = r.random(n.shape) < 0.035
    rgb[peb] = (175, 170, 160)
    rgb[np.roll(peb, -1, 0)] = (90, 75, 60)
    return rgb


def t_water(v, a, b, inside, r):
    n = fbm(a, b, 3, v, (4, 8, 16))
    wave = np.sin(2 * math.pi * (a * 2 + b * 3) + n * 6)
    rgb = quant(0.6 * n + 0.2 * (wave * 0.5 + 0.5) + 0.2 * r.random(n.shape) * 0.5,
                palette((30, 60, 95), (70, 125, 165)))
    rgb[(wave > 0.92) & (r.random(n.shape) < 0.5)] = (170, 205, 225)
    return rgb


def t_sand(v, a, b, inside, r, dune=False):
    n = fbm(a, b, 4, v)
    rip = np.sin(2 * math.pi * (a * 3 + b * 5) + n * 5)
    k = 0.45 if dune else 0.18
    pal = palette((170, 130, 80), (238, 210, 150)) if not dune else palette((150, 108, 65), (228, 196, 135))
    rgb = quant((1 - k) * (0.7 * n + 0.3 * r.random(n.shape)) + k * (rip * 0.5 + 0.5), pal)
    return rgb


def t_cracked(v, a, b, inside, r):
    n = fbm(a, b, 5, v)
    rgb = quant(0.7 * n + 0.3 * r.random(n.shape), palette((165, 125, 85), (220, 180, 130)))
    e = voronoi_edges(a, b, 50 + v, 5)
    rgb[e < 0.025] = (115, 80, 55)
    return rgb


def t_snow(v, a, b, inside, r, trodden=False):
    n = fbm(a, b, 6, v)
    pal = palette((175, 190, 215), (250, 252, 255)) if not trodden else palette((150, 158, 175), (220, 225, 235))
    rgb = quant(0.75 * n + 0.25 * r.random(n.shape), pal)
    rgb[r.random(n.shape) < 0.01] = (255, 255, 255)
    if trodden:
        steps = pnoise(a, b, 16, 70 + v) > 0.78
        rgb[steps] *= 0.88
    return rgb


def t_ice(v, a, b, inside, r):
    n = fbm(a, b, 7, v, (4, 8, 16))
    streak = np.sin(2 * math.pi * (a * 4 - b * 2) + n * 3)
    rgb = quant(0.6 * n + 0.4 * (streak * 0.5 + 0.5), palette((120, 170, 205), (205, 232, 245)))
    e = voronoi_edges(a, b, 80 + v, 4)
    rgb[e < 0.018] = (235, 248, 255)
    return rgb


TILES = {
    "grass": t_grass,
    "grass_flowers": lambda v, a, b, i, r: t_grass(v, a, b, i, r, flowers=True),
    "forest_floor": lambda v, a, b, i, r: t_grass(v, a, b, i, r, base=((30, 52, 28), (95, 125, 55)), litter=True),
    "path": t_path,
    "water": t_water,
    "sand": t_sand,
    "dune": lambda v, a, b, i, r: t_sand(v, a, b, i, r, dune=True),
    "cracked_earth": t_cracked,
    "snow": t_snow,
    "snow_path": lambda v, a, b, i, r: t_snow(v, a, b, i, r, trodden=True),
    "ice": t_ice,
}
VARIANTS = 3


def build_tiles():
    out = os.path.join(ART, "Tiles")
    os.makedirs(out, exist_ok=True)
    a, b, inside = tile_coords()
    for name, fn in TILES.items():
        sheet = np.zeros((TH, TW * VARIANTS, 4), np.uint8)
        for v in range(VARIANTS):
            r = np.random.default_rng(sum(map(ord, name)) * 31 + v)
            sheet[:, v * TW:(v + 1) * TW] = tile_img(fn(v, a, b, inside, r), inside)
        Image.fromarray(sheet, "RGBA").save(os.path.join(out, f"{name}.png"))
        print("tile", name)


if __name__ == "__main__":
    what = sys.argv[1:] or ["tiles", "props", "characters", "portraits"]
    if "tiles" in what:
        build_tiles()
    if "props" in what:
        build_props()
    if "portraits" in what:
        build_portraits()
    if "characters" in what:
        for c in CHARACTERS:
            build_character(c)
