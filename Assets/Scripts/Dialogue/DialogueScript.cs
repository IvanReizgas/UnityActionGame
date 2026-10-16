using System.Collections.Generic;
using UnityEngine;

// Parses dialogue files from Resources/Dialogue/<name>.txt. Syntax:
//
//   # node_name                 start a node (conversations begin at "start")
//   speaker: Text to say.       a line; speaker is an npc id from npcs.txt, or "you"
//   Plain text                  narration (no speaker)
//   * Reply text -> node        a player choice (shown together with the choices that follow it)
//   -> node                     jump ("-> end" closes the conversation)
//   ~ action                    run an action, e.g. "~ set met_elder", "~ gold 25"
//   [condition] ...             any line can start with a condition, e.g. "[gold>=10 & !bought]"
//   // comment
public class DialogueScript
{
    public enum Kind { Line, Choice, Jump, Action }

    public class Step
    {
        public Kind kind;
        public string condition, speaker, text, target;
    }

    public readonly Dictionary<string, List<Step>> nodes = new Dictionary<string, List<Step>>();
    public string Name { get; private set; }

    static readonly Dictionary<string, DialogueScript> cache = new Dictionary<string, DialogueScript>();

    public static DialogueScript Load(string name)
    {
        if (cache.TryGetValue(name, out var s)) return s;
        var ta = Resources.Load<TextAsset>("Dialogue/" + name);
        if (ta == null)
        {
            Debug.LogWarning($"Missing Resources/Dialogue/{name}.txt");
            s = Parse(name, "# start\n...\n");
        }
        else s = Parse(name, ta.text);
        cache[name] = s;
        return s;
    }

    public static DialogueScript Parse(string name, string source)
    {
        var script = new DialogueScript { Name = name };
        List<Step> current = null;
        int lineNo = 0;
        foreach (var raw in source.Split('\n'))
        {
            lineNo++;
            var line = raw.Trim();
            if (line.Length == 0 || line.StartsWith("//")) continue;
            if (line.StartsWith("#"))
            {
                current = new List<Step>();
                script.nodes[line.Substring(1).Trim()] = current;
                continue;
            }
            if (current == null)
            {
                Debug.LogWarning($"{name}.txt:{lineNo}: text before the first '# node'");
                continue;
            }

            var step = new Step();
            if (line.StartsWith("["))
            {
                int close = line.IndexOf(']');
                if (close > 0)
                {
                    step.condition = line.Substring(1, close - 1).Trim();
                    line = line.Substring(close + 1).Trim();
                }
            }

            if (line.StartsWith("*"))
            {
                step.kind = Kind.Choice;
                SplitArrow(line.Substring(1), out step.text, out step.target);
            }
            else if (line.StartsWith("->"))
            {
                step.kind = Kind.Jump;
                step.target = line.Substring(2).Trim();
            }
            else if (line.StartsWith("~"))
            {
                step.kind = Kind.Action;
                step.text = line.Substring(1).Trim();
            }
            else
            {
                step.kind = Kind.Line;
                int colon = line.IndexOf(':');
                if (colon > 0 && line.Substring(0, colon).IndexOf(' ') < 0)
                {
                    step.speaker = line.Substring(0, colon).Trim();
                    step.text = line.Substring(colon + 1).Trim();
                }
                else step.text = line;
            }
            current.Add(step);
        }
        return script;
    }

    static void SplitArrow(string s, out string text, out string target)
    {
        int arrow = s.LastIndexOf("->");
        if (arrow >= 0)
        {
            text = s.Substring(0, arrow).Trim();
            target = s.Substring(arrow + 2).Trim();
        }
        else
        {
            text = s.Trim();
            target = "end";
        }
    }
}
