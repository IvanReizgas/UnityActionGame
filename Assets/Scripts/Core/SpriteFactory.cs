using System;
using System.Collections.Generic;
using UnityEngine;

// Tiny procedural sprites for effects and loot (shadows, sparks, slash arcs, coins).
// Characters, tiles and props come from Resources/Art via ArtLibrary instead.
public static class SpriteFactory
{
    static readonly Dictionary<string, Sprite> cache = new Dictionary<string, Sprite>();

    public static Sprite Orb => Get("orb", 8, 8, 24, new Vector2(0.5f, 0.5f), (x, y) =>
    {
        float d = Vector2.Distance(new Vector2(x + 0.5f, y + 0.5f), new Vector2(4, 4)) / 4f;
        if (d > 1f) return Clear;
        return new Color32(255, 255, 255, (byte)(255 * Mathf.Clamp01(1.4f - d)));
    });

    public static Sprite Shadow => Get("shadow", 16, 8, 32, new Vector2(0.5f, 0.5f), (x, y) =>
    {
        float nx = (x + 0.5f - 8f) / 8f, ny = (y + 0.5f - 4f) / 4f;
        return nx * nx + ny * ny <= 1f ? new Color32(0, 0, 0, 80) : Clear;
    });

    public static Sprite Coin => Get("coin", 6, 6, 64, new Vector2(0.5f, 0f), (x, y) =>
    {
        float d = Vector2.Distance(new Vector2(x + 0.5f, y + 0.5f), new Vector2(3, 3));
        if (d > 3f) return Clear;
        return d > 2f ? new Color32(150, 110, 30, 255) : new Color32(255, 215, 80, 255);
    });

    public static Sprite Potion => Get("potion", 6, 9, 64, new Vector2(0.5f, 0f), (x, y) =>
    {
        if (y >= 6) return x >= 2 && x <= 3 ? new Color32(200, 200, 210, 255) : Clear;
        float d = Vector2.Distance(new Vector2(x + 0.5f, y + 0.5f), new Vector2(3, 3));
        if (d > 3f) return Clear;
        return d > 2f ? new Color32(120, 20, 30, 255) : new Color32(230, 50, 60, 255);
    });

    // Sword-swing crescent facing +X, drawn flat on the ground (Fx squashes it isometrically).
    public static Sprite Arc => Get("arc", 32, 32, 32, new Vector2(0.5f, 0.5f), (x, y) =>
    {
        var p = new Vector2(x + 0.5f - 16f, y + 0.5f - 16f);
        float d = p.magnitude / 16f;
        float ang = Mathf.Abs(Mathf.Atan2(p.y, p.x) * Mathf.Rad2Deg);
        if (d > 1f || d < 0.6f || ang > 75f) return Clear;
        float a = (1f - ang / 75f) * Mathf.Clamp01((d - 0.6f) * 4f);
        return new Color32(255, 255, 255, (byte)(200 * a));
    });

    public static Sprite Missing => Get("missing", 16, 16, 16, new Vector2(0.5f, 0f), (x, y) =>
        ((x / 4 + y / 4) % 2 == 0) ? new Color32(255, 0, 255, 255) : new Color32(0, 0, 0, 255));

    static readonly Color32 Clear = new Color32(0, 0, 0, 0);

    static Sprite Get(string key, int w, int h, float ppu, Vector2 pivot, Func<int, int, Color32> pixel)
    {
        if (cache.TryGetValue(key, out var s) && s != null) return s;
        var tex = new Texture2D(w, h, TextureFormat.RGBA32, false)
        {
            filterMode = FilterMode.Point,
            wrapMode = TextureWrapMode.Clamp,
            name = key,
        };
        var px = new Color32[w * h];
        for (int y = 0; y < h; y++)
            for (int x = 0; x < w; x++)
                px[y * w + x] = pixel(x, y);
        tex.SetPixels32(px);
        tex.Apply();
        s = Sprite.Create(tex, new Rect(0, 0, w, h), pivot, ppu, 0, SpriteMeshType.FullRect);
        s.name = key;
        cache[key] = s;
        return s;
    }
}
