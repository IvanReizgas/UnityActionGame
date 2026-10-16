using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Tilemaps;

// Loads (and caches) all art from Assets/Resources/Art following ART_SPEC.md.
// Swap any PNG for hand-made art with the same layout and it is picked up automatically.
public static class ArtLibrary
{
    public const int PPU = 64;
    public const int TileWidth = 64, TileHeight = 32;

    static readonly Dictionary<string, CharacterSheet> sheets = new Dictionary<string, CharacterSheet>();
    static readonly Dictionary<string, Tile[]> tiles = new Dictionary<string, Tile[]>();
    static readonly Dictionary<string, Texture2D> portraits = new Dictionary<string, Texture2D>();
    static Dictionary<string, PropDef> props;

    public static CharacterSheet Character(string name)
    {
        if (!sheets.TryGetValue(name, out var s))
            sheets[name] = s = CharacterSheet.Load(name);
        return s;
    }

    // Tiles: Art/Tiles/<name>.png, 64x32 diamonds, variants side by side.
    public static Tile Tile(string name, int x, int y)
    {
        if (!tiles.TryGetValue(name, out var variants))
            tiles[name] = variants = LoadTile(name);
        int h = (x * 73856093) ^ (y * 19349663);
        return variants[(h & 0x7fffffff) % variants.Length];
    }

    static Tile[] LoadTile(string name)
    {
        var tex = Resources.Load<Texture2D>("Art/Tiles/" + name);
        if (tex == null)
        {
            Debug.LogWarning($"Missing tile Art/Tiles/{name}.png");
            return new[] { MakeTile(SpriteFactory.Missing) };
        }
        tex.filterMode = FilterMode.Point;
        int count = Mathf.Max(1, tex.width / TileWidth);
        var result = new Tile[count];
        for (int i = 0; i < count; i++)
        {
            var s = Sprite.Create(tex, new Rect(i * TileWidth, 0, TileWidth, TileHeight), new Vector2(0.5f, 0.5f),
                PPU, 0, SpriteMeshType.FullRect);
            s.name = $"{name}_{i}";
            result[i] = MakeTile(s);
        }
        return result;
    }

    static Tile MakeTile(Sprite s)
    {
        var t = ScriptableObject.CreateInstance<Tile>();
        t.sprite = s;
        t.colliderType = UnityEngine.Tilemaps.Tile.ColliderType.None;
        t.flags = TileFlags.None; // allow per-cell colour variation
        return t;
    }

    public static PropDef Prop(string name)
    {
        if (props == null) LoadProps();
        if (!props.TryGetValue(name, out var def))
        {
            Debug.LogWarning($"Unknown prop '{name}'");
            props[name] = def = new PropDef { name = name, pivotX = 8, pivotY = 0, colliderType = "none" };
            def.sprite = SpriteFactory.Missing;
        }
        if (def.sprite == null)
        {
            var tex = Resources.Load<Texture2D>("Art/Props/" + name);
            if (tex == null)
            {
                Debug.LogWarning($"Missing Art/Props/{name}.png");
                def.sprite = SpriteFactory.Missing;
            }
            else
            {
                tex.filterMode = FilterMode.Point;
                def.sprite = Sprite.Create(tex, new Rect(0, 0, tex.width, tex.height),
                    new Vector2(def.pivotX / (float)tex.width, def.pivotY / (float)tex.height), PPU, 0,
                    SpriteMeshType.FullRect);
                def.sprite.name = name;
            }
        }
        return def;
    }

    static void LoadProps()
    {
        props = new Dictionary<string, PropDef>();
        var json = Resources.Load<TextAsset>("Art/Props/props");
        if (json == null) return;
        foreach (var p in JsonUtility.FromJson<PropList>(json.text).props)
            props[p.name] = p;
    }

    public static Texture2D Portrait(string name)
    {
        if (string.IsNullOrEmpty(name)) return null;
        if (!portraits.TryGetValue(name, out var tex))
        {
            tex = Resources.Load<Texture2D>("Art/Portraits/" + name);
            if (tex) tex.filterMode = FilterMode.Point;
            portraits[name] = tex;
        }
        return tex;
    }
}

[Serializable]
public class PropDef
{
    public string name;
    public int pivotX, pivotY;
    public string colliderType = "none"; // none | ellipse | diamond
    public float radius, halfWidth, halfHeight;
    public float offsetX, offsetY;        // in grid cells, for multi-cell props
    public bool fade;                     // turn see-through when the player walks behind it
    [NonSerialized] public Sprite sprite;
}

[Serializable]
class PropList
{
    public PropDef[] props;
}
