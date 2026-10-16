using System.Collections.Generic;
using System.Globalization;
using UnityEngine;
using UnityEngine.Tilemaps;

// A handcrafted area loaded from Resources/Regions/<id>.txt (format described in the file header).
public class Region
{
    public static Region Current { get; private set; }

    // Ground tiles that cannot be walked on.
    static readonly HashSet<string> BlockingTiles = new HashSet<string> { "water" };

    struct LegendEntry
    {
        public string tile, obj;
    }

    public string Id { get; private set; }
    public string Name { get; private set; } = "";
    public Color Ambient { get; private set; } = Color.white;
    public int Width { get; private set; }
    public int Height { get; private set; }
    public readonly Dictionary<string, Vector2> entries = new Dictionary<string, Vector2>();

    readonly Dictionary<char, LegendEntry> legend = new Dictionary<char, LegendEntry>();
    char[,] cells;
    bool[,] blocked;
    Grid grid;

    public static Region Load(string id, Transform root)
    {
        var ta = Resources.Load<TextAsset>("Regions/" + id);
        if (ta == null)
        {
            Debug.LogError($"Missing Resources/Regions/{id}.txt");
            return null;
        }
        var r = new Region { Id = id };
        r.Parse(ta.text);
        Current = r;
        r.Build(root);
        return r;
    }

    void Parse(string text)
    {
        var rows = new List<string>();
        string section = "";
        foreach (var raw in text.Replace("\r", "").Split('\n'))
        {
            if (section != "map" && (raw.TrimStart().StartsWith("#") || raw.Trim().Length == 0)) continue;
            var line = raw.TrimEnd();
            if (line.StartsWith("[") && line.EndsWith("]"))
            {
                section = line.Substring(1, line.Length - 2).Trim().ToLowerInvariant();
                continue;
            }
            if (section == "map")
            {
                if (line.Length > 0) rows.Add(line);
            }
            else if (section == "legend")
            {
                var parts = line.Trim().Split(new[] { ' ', '\t' }, System.StringSplitOptions.RemoveEmptyEntries);
                if (parts.Length >= 2 && parts[0].Length == 1)
                    legend[parts[0][0]] = new LegendEntry { tile = parts[1], obj = parts.Length > 2 ? parts[2] : null };
            }
            else
            {
                int colon = line.IndexOf(':');
                if (colon < 0) continue;
                var key = line.Substring(0, colon).Trim().ToLowerInvariant();
                var value = line.Substring(colon + 1).Trim();
                if (key == "name") Name = value;
                else if (key == "ambient")
                {
                    var c = value.Split(' ');
                    if (c.Length >= 3)
                        Ambient = new Color(F(c[0]), F(c[1]), F(c[2]));
                }
            }
        }

        Height = rows.Count;
        Width = 0;
        foreach (var r in rows) Width = Mathf.Max(Width, r.Length);
        cells = new char[Width, Height];
        blocked = new bool[Width, Height];
        for (int row = 0; row < Height; row++)
            for (int x = 0; x < Width; x++)
                cells[x, Height - 1 - row] = x < rows[row].Length ? rows[row][x] : ' ';
    }

    static float F(string s) => float.Parse(s, CultureInfo.InvariantCulture);

    void Build(Transform root)
    {
        var gridGo = Iso.Child(root, "Grid");
        grid = gridGo.AddComponent<Grid>();
        grid.cellLayout = GridLayout.CellLayout.Isometric;
        grid.cellSize = new Vector3(1f, Iso.YScale, 1f);

        var groundGo = Iso.Child(gridGo.transform, "Ground");
        var ground = groundGo.AddComponent<Tilemap>();
        groundGo.AddComponent<TilemapRenderer>().sortingOrder = Iso.FloorOrder;
        ground.color = Ambient;

        var objects = Iso.Child(root, "Objects").transform;
        var cellX = CellCenter(1, 0) - CellCenter(0, 0);
        var cellY = CellCenter(0, 1) - CellCenter(0, 0);

        for (int x = 0; x < Width; x++)
        {
            for (int y = 0; y < Height; y++)
            {
                char c = cells[x, y];
                if (!legend.TryGetValue(c, out var e))
                {
                    blocked[x, y] = true;
                    if (c != ' ') Debug.LogWarning($"Region {Id}: no legend entry for '{c}'");
                    continue;
                }
                var cell = new Vector3Int(x, y, 0);
                ground.SetTile(cell, ArtLibrary.Tile(e.tile, x, y));
                // gentle large-scale brightness variation so repeated tiles don't look like a grid
                float v = 0.93f + 0.1f * Mathf.PerlinNoise(x * 0.13f + 7.1f, y * 0.13f + 3.3f);
                ground.SetColor(cell, new Color(v, v, v));
                if (BlockingTiles.Contains(e.tile)) blocked[x, y] = true;
                if (!string.IsNullOrEmpty(e.obj)) PlaceObject(e.obj, x, y, objects, cellX, cellY);
            }
        }
        PadBorder(ground);
        BuildBlockers(root);
    }

    // Repeat the outermost ground tiles beyond the map edge so the world doesn't end in a void.
    void PadBorder(Tilemap ground)
    {
        const int pad = 10;
        for (int x = -pad; x < Width + pad; x++)
        {
            for (int y = -pad; y < Height + pad; y++)
            {
                if (x >= 0 && y >= 0 && x < Width && y < Height) continue;
                int cx = Mathf.Clamp(x, 0, Width - 1), cy = Mathf.Clamp(y, 0, Height - 1);
                if (!legend.TryGetValue(cells[cx, cy], out var e)) continue;
                var cell = new Vector3Int(x, y, 0);
                ground.SetTile(cell, ArtLibrary.Tile(e.tile, x, y));
                float dist = Mathf.Max(Mathf.Max(-x, x - Width + 1), Mathf.Max(-y, y - Height + 1));
                float v = Mathf.Lerp(0.9f, 0.35f, dist / pad); // darken toward the edge of the world
                ground.SetColor(cell, new Color(v, v, v));
            }
        }
    }

    void PlaceObject(string obj, int x, int y, Transform parent, Vector2 cellX, Vector2 cellY)
    {
        var pos = CellCenter(x, y);
        var parts = obj.Split(':');
        switch (parts[0])
        {
            case "npc":
                var npc = GameData.Npc(parts[1]);
                if (npc != null) Npc.Spawn(npc, pos, parent);
                else Debug.LogWarning($"Unknown npc '{parts[1]}'");
                break;
            case "enemy":
                var enemy = GameData.Enemy(parts[1]);
                if (enemy != null) Enemy.Spawn(enemy, pos, parent);
                else Debug.LogWarning($"Unknown enemy '{parts[1]}'");
                break;
            case "entry":
                entries[parts[1]] = pos;
                break;
            case "exit":
                if (parts.Length >= 3) ExitTrigger.Create(parent, pos, parts[1], parts[2]);
                break;
            default:
                var def = ArtLibrary.Prop(parts[0]);
                Prop.Create(def, pos + cellX * def.offsetX + cellY * def.offsetY, parent, Ambient);
                break;
        }
    }

    // One collider holding a diamond per blocked cell, plus a ring around the map edge.
    void BuildBlockers(Transform root)
    {
        var go = Iso.Child(root, "Blockers");
        var col = go.AddComponent<PolygonCollider2D>();
        var paths = new List<Vector2[]>();
        for (int x = -1; x <= Width; x++)
        {
            for (int y = -1; y <= Height; y++)
            {
                bool outside = x < 0 || y < 0 || x >= Width || y >= Height;
                if (!outside && !blocked[x, y]) continue;
                if (!outside && !TouchesWalkable(x, y)) continue;
                if (outside && !TouchesWalkable(x, y)) continue;
                var c = CellCenter(x, y);
                paths.Add(new[]
                {
                    c + new Vector2(0.5f, 0f), c + new Vector2(0f, 0.25f), c + new Vector2(-0.5f, 0f), c + new Vector2(0f, -0.25f),
                });
            }
        }
        col.pathCount = paths.Count;
        for (int i = 0; i < paths.Count; i++) col.SetPath(i, paths[i]);
    }

    bool TouchesWalkable(int x, int y)
    {
        for (int ox = -1; ox <= 1; ox++)
            for (int oy = -1; oy <= 1; oy++)
            {
                int nx = x + ox, ny = y + oy;
                if (nx >= 0 && ny >= 0 && nx < Width && ny < Height && !blocked[nx, ny]) return true;
            }
        return false;
    }

    public Vector2 CellCenter(int x, int y) => grid.GetCellCenterWorld(new Vector3Int(x, y, 0));

    public bool IsBlocked(Vector2 world)
    {
        var c = grid.WorldToCell(world);
        return c.x < 0 || c.y < 0 || c.x >= Width || c.y >= Height || blocked[c.x, c.y];
    }

    public Vector2 Entry(string id)
    {
        if (entries.TryGetValue(id, out var p)) return p;
        Debug.LogWarning($"Region {Id} has no entry '{id}'");
        foreach (var e in entries.Values) return e;
        return CellCenter(Width / 2, Height / 2);
    }
}
