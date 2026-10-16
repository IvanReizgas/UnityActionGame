using System.Collections.Generic;
using UnityEngine;

// Steps through a DialogueScript. The UI reads Speaker/Text/Choices and calls Continue() or Choose().
public class DialogueRunner
{
    public class Choice
    {
        public string text, target;
    }

    public string Speaker { get; private set; }
    public string Text { get; private set; }
    public readonly List<Choice> Choices = new List<Choice>();
    public bool Finished { get; private set; }

    DialogueScript script;
    List<DialogueScript.Step> steps;
    int index;
    int guard;

    public void Start(DialogueScript s, string node = "start")
    {
        script = s;
        Finished = false;
        Goto(node);
        Advance();
    }

    public void Continue()
    {
        if (Finished || Choices.Count > 0) return;
        Advance();
    }

    public void Choose(int i)
    {
        if (i < 0 || i >= Choices.Count) return;
        var target = Choices[i].target;
        Choices.Clear();
        Goto(target);
        Advance();
    }

    void Goto(string node)
    {
        if (node == "end" || !script.nodes.TryGetValue(node, out steps))
        {
            if (node != "end") Debug.LogWarning($"Dialogue '{script.Name}': no node '{node}'");
            Finish();
            return;
        }
        index = 0;
    }

    void Finish()
    {
        Finished = true;
        steps = null;
        Choices.Clear();
    }

    void Advance()
    {
        guard = 0;
        while (!Finished)
        {
            if (++guard > 1000)
            {
                Debug.LogError($"Dialogue '{script.Name}' looped without showing anything");
                Finish();
                return;
            }
            if (index >= steps.Count)
            {
                Finish();
                return;
            }
            var step = steps[index++];
            if (step.kind == DialogueScript.Kind.Choice)
            {
                // gather this choice and every consecutive one
                index--;
                while (index < steps.Count && steps[index].kind == DialogueScript.Kind.Choice)
                {
                    var c = steps[index++];
                    if (WorldState.Check(c.condition))
                        Choices.Add(new Choice { text = WorldState.Interpolate(c.text), target = c.target });
                }
                if (Choices.Count > 0) return;
                continue;
            }
            if (!WorldState.Check(step.condition)) continue;
            switch (step.kind)
            {
                case DialogueScript.Kind.Action:
                    WorldState.Execute(step.text);
                    break;
                case DialogueScript.Kind.Jump:
                    Goto(step.target);
                    break;
                case DialogueScript.Kind.Line:
                    Speaker = step.speaker;
                    Text = WorldState.Interpolate(step.text);
                    // if choices follow directly, show them together with this line
                    if (index < steps.Count && steps[index].kind == DialogueScript.Kind.Choice)
                    {
                        while (index < steps.Count && steps[index].kind == DialogueScript.Kind.Choice)
                        {
                            var c = steps[index++];
                            if (WorldState.Check(c.condition))
                                Choices.Add(new Choice { text = WorldState.Interpolate(c.text), target = c.target });
                        }
                    }
                    return;
            }
        }
    }
}
