using System.Collections.Generic;
using UnityEngine;

// Pipe-separated tables in Resources/Data. Lines starting with # are comments.
public class NpcDef
{
    public string id, name, sheet, portrait, dialogue;
    public bool wander;
}

public class EnemyDef
{
    public string id, name, sheet;
    public float hp, damage, speed, aggroRange, attackRange, footRadius;
    public int xp, gold;
}

public static class GameData
{
    static Dictionary<string, NpcDef> npcs;
    static Dictionary<string, EnemyDef> enemies;

    public static NpcDef Npc(string id)
    {
        if (npcs == null) LoadNpcs();
        return npcs.TryGetValue(id, out var d) ? d : null;
    }

    public static EnemyDef Enemy(string id)
    {
        if (enemies == null) LoadEnemies();
        return enemies.TryGetValue(id, out var d) ? d : null;
    }

    static IEnumerable<string[]> Rows(string resource)
    {
        var ta = Resources.Load<TextAsset>(resource);
        if (ta == null)
        {
            Debug.LogError($"Missing Resources/{resource}.txt");
            yield break;
        }
        foreach (var raw in ta.text.Split('\n'))
        {
            var line = raw.Trim();
            if (line.Length == 0 || line.StartsWith("#")) continue;
            var cols = line.Split('|');
            for (int i = 0; i < cols.Length; i++) cols[i] = cols[i].Trim();
            yield return cols;
        }
    }

    static void LoadNpcs()
    {
        npcs = new Dictionary<string, NpcDef>();
        foreach (var c in Rows("Data/npcs"))
        {
            if (c.Length < 6) continue;
            npcs[c[0]] = new NpcDef
            {
                id = c[0], name = c[1], sheet = c[2], portrait = c[3], dialogue = c[4], wander = c[5] == "wander",
            };
        }
    }

    static void LoadEnemies()
    {
        enemies = new Dictionary<string, EnemyDef>();
        var ci = System.Globalization.CultureInfo.InvariantCulture;
        foreach (var c in Rows("Data/enemies"))
        {
            if (c.Length < 11) continue;
            enemies[c[0]] = new EnemyDef
            {
                id = c[0], name = c[1], sheet = c[2],
                hp = float.Parse(c[3], ci), damage = float.Parse(c[4], ci), speed = float.Parse(c[5], ci),
                xp = int.Parse(c[6]), gold = int.Parse(c[7]),
                aggroRange = float.Parse(c[8], ci), attackRange = float.Parse(c[9], ci), footRadius = float.Parse(c[10], ci),
            };
        }
    }
}
