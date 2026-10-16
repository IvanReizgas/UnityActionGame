using System;
using System.Collections.Generic;
using UnityEngine;

// A character's animations, loaded from Resources/Art/Characters/<name>/ (see ART_SPEC.md).
// Each animation is one PNG: columns = frames, rows = directions.
//   8 rows: S, SW, W, NW, N, NE, E, SE
//   5 rows: S, SW, W, NW, N            (east-facing rows are mirrored)
//   1 row : side view facing east       (mirrored when facing west)
public class CharacterSheet
{
    public const int DirCount = 8;

    public class Anim
    {
        public string name;
        public int frames, rows, hitFrame;
        public float fps;
        public bool loop;
        public Sprite[] sprites; // rows * frames, row-major
        public float Duration => frames / Mathf.Max(0.01f, fps);
    }

    [Serializable]
    class SheetJson
    {
        public int frameWidth = 64, frameHeight = 64, pivotX = 32, pivotY = 10, ppu = 64;
        public AnimJson[] animations;
    }

    [Serializable]
    class AnimJson
    {
        public string name, file;
        public int frames = 1;
        public float fps = 8;
        public bool loop = true;
        public int hitFrame = -1;
    }

    public string Name { get; private set; }
    readonly Dictionary<string, Anim> anims = new Dictionary<string, Anim>();

    public Anim Get(string name) => anims.TryGetValue(name, out var a) ? a : null;
    public bool Has(string name) => anims.ContainsKey(name);

    public static CharacterSheet Load(string name)
    {
        var sheet = new CharacterSheet { Name = name };
        string dir = $"Art/Characters/{name}/";
        var json = Resources.Load<TextAsset>(dir + "character");
        if (json == null)
        {
            Debug.LogWarning($"Character '{name}' has no {dir}character.json, using placeholder");
            sheet.anims["idle"] = new Anim
            {
                name = "idle", frames = 1, rows = 1, fps = 1, loop = true, hitFrame = -1,
                sprites = new[] { SpriteFactory.Missing },
            };
            return sheet;
        }

        var data = JsonUtility.FromJson<SheetJson>(json.text);
        foreach (var a in data.animations)
        {
            var tex = Resources.Load<Texture2D>(dir + a.file);
            if (tex == null)
            {
                Debug.LogWarning($"Missing {dir}{a.file}.png");
                continue;
            }
            tex.filterMode = FilterMode.Point;
            int rows = Mathf.Max(1, tex.height / data.frameHeight);
            int frames = Mathf.Min(a.frames, tex.width / data.frameWidth);
            var anim = new Anim
            {
                name = a.name, frames = frames, rows = rows, fps = a.fps, loop = a.loop, hitFrame = a.hitFrame,
                sprites = new Sprite[rows * frames],
            };
            var pivot = new Vector2(data.pivotX / (float)data.frameWidth, data.pivotY / (float)data.frameHeight);
            for (int r = 0; r < rows; r++)
            {
                for (int f = 0; f < frames; f++)
                {
                    var rect = new Rect(f * data.frameWidth, tex.height - (r + 1) * data.frameHeight,
                        data.frameWidth, data.frameHeight);
                    var s = Sprite.Create(tex, rect, pivot, data.ppu, 0, SpriteMeshType.FullRect);
                    s.name = $"{name}_{a.name}_{r}_{f}";
                    anim.sprites[r * frames + f] = s;
                }
            }
            sheet.anims[a.name] = anim;
        }
        return sheet;
    }

    // dir: 0..7 in DIR order (S, SW, W, NW, N, NE, E, SE)
    public static Sprite Frame(Anim anim, int dir, int frame, out bool flip)
    {
        flip = false;
        int row;
        if (anim.rows >= 8) row = dir;
        else if (anim.rows >= 5)
        {
            if (dir <= 4) row = dir;
            else { row = 8 - dir; flip = true; } // NE->NW, E->W, SE->SW
        }
        else
        {
            row = 0;
            flip = dir >= 1 && dir <= 3; // side view faces east; mirror for westward
        }
        frame = Mathf.Clamp(frame, 0, anim.frames - 1);
        return anim.sprites[row * anim.frames + frame];
    }

    // Ground-space direction -> sheet direction index.
    public static int DirIndex(Vector2 groundDir)
    {
        float angle = Mathf.Atan2(groundDir.y, groundDir.x) * Mathf.Rad2Deg;
        return Mathf.RoundToInt(Mathf.Repeat(270f - angle, 360f) / 45f) % DirCount;
    }

    public static Vector2 DirVector(int dir)
    {
        float a = (270f - dir * 45f) * Mathf.Deg2Rad;
        return new Vector2(Mathf.Cos(a), Mathf.Sin(a));
    }
}
