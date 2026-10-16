using System.Collections.Generic;
using System.Text.RegularExpressions;
using UnityEngine;

// Global story variables used by dialogue conditions and actions.
// Every variable is an int; a "flag" is just a variable that is 0 or not.
// Built-in read-only values: gold, potions, level, hp. Enemy kills count up "killed_<enemy id>".
public static class WorldState
{
    static readonly Dictionary<string, int> vars = new Dictionary<string, int>();
    static readonly Regex Compare = new Regex(@"^(!?)([A-Za-z_][\w]*)\s*(>=|<=|==|!=|>|<)?\s*(-?\d+)?$");

    public static void Reset() => vars.Clear();

    public static int Get(string name)
    {
        var p = Player.Instance;
        switch (name)
        {
            case "gold": return p ? p.Gold : 0;
            case "potions": return p ? p.Potions : 0;
            case "level": return p ? p.Level : 0;
            case "hp": return p ? Mathf.CeilToInt(p.Health.Current) : 0;
        }
        return vars.TryGetValue(name, out var v) ? v : 0;
    }

    public static void Set(string name, int value) => vars[name] = value;
    public static void Add(string name, int delta) => vars[name] = Get(name) + delta;

    // "quest_wolves==1 & killed_wolf>=3", "met_elder", "!met_elder"
    public static bool Check(string condition)
    {
        if (string.IsNullOrWhiteSpace(condition)) return true;
        foreach (var raw in condition.Split('&'))
        {
            var term = raw.Trim();
            var m = Compare.Match(term);
            if (!m.Success)
            {
                Debug.LogWarning($"Bad condition '{term}'");
                return false;
            }
            bool negate = m.Groups[1].Value == "!";
            int value = Get(m.Groups[2].Value);
            bool ok;
            if (m.Groups[3].Success && m.Groups[4].Success)
            {
                int rhs = int.Parse(m.Groups[4].Value);
                switch (m.Groups[3].Value)
                {
                    case ">=": ok = value >= rhs; break;
                    case "<=": ok = value <= rhs; break;
                    case "==": ok = value == rhs; break;
                    case "!=": ok = value != rhs; break;
                    case ">": ok = value > rhs; break;
                    default: ok = value < rhs; break;
                }
            }
            else ok = value != 0;
            if (negate) ok = !ok;
            if (!ok) return false;
        }
        return true;
    }

    // set <var> [value] | add <var> <n> | gold <n> | potion <n> | xp <n> | heal
    public static void Execute(string action)
    {
        var parts = action.Trim().Split(new[] { ' ', '\t' }, System.StringSplitOptions.RemoveEmptyEntries);
        if (parts.Length == 0) return;
        int Arg(int i, int fallback) => parts.Length > i && int.TryParse(parts[i], out var v) ? v : fallback;
        var p = Player.Instance;
        switch (parts[0])
        {
            case "set": if (parts.Length > 1) Set(parts[1], Arg(2, 1)); break;
            case "add": if (parts.Length > 1) Add(parts[1], Arg(2, 1)); break;
            case "gold": if (p) p.AddGold(Arg(1, 0)); break;
            case "potion": if (p) p.AddPotions(Arg(1, 1)); break;
            case "xp": if (p) p.AddXp(Arg(1, 0)); break;
            case "heal": if (p) p.Health.Heal(p.Health.Max); break;
            default: Debug.LogWarning($"Unknown dialogue action '{action}'"); break;
        }
    }

    static readonly Regex Var = new Regex(@"\{(\w+)\}");
    public static string Interpolate(string text) => Var.Replace(text, m => Get(m.Groups[1].Value).ToString());
}
