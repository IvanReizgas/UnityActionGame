using System.Collections.Generic;
using UnityEngine;

// Damage numbers and pop-up messages anchored to world positions, drawn by the HUD.
public static class FloatingText
{
    const float Life = 0.9f;

    struct Entry
    {
        public Vector3 pos;
        public string text;
        public Color color;
        public float size, t;
    }

    static readonly List<Entry> entries = new List<Entry>();

    public static void Add(Vector3 worldPos, string text, Color color, float size = 1f)
    {
        entries.Add(new Entry
        {
            pos = worldPos + (Vector3)(Random.insideUnitCircle * 0.15f),
            text = text,
            color = color,
            size = size,
        });
    }

    public static void Clear() => entries.Clear();

    public static void Tick(float dt)
    {
        for (int i = entries.Count - 1; i >= 0; i--)
        {
            var e = entries[i];
            e.t += dt;
            if (e.t >= Life) entries.RemoveAt(i);
            else entries[i] = e;
        }
    }

    public static void Draw(Camera cam, GUIStyle style)
    {
        int baseSize = style.fontSize;
        foreach (var e in entries)
        {
            var sp = cam.WorldToScreenPoint(e.pos + Vector3.up * (e.t * 0.8f));
            float a = 1f - e.t / Life;
            style.fontSize = Mathf.RoundToInt(baseSize * e.size);
            var r = new Rect(sp.x - 100, Screen.height - sp.y - 20, 200, 40);
            GUI.color = new Color(0, 0, 0, a * 0.8f);
            GUI.Label(new Rect(r.x + 2, r.y + 2, r.width, r.height), e.text, style);
            GUI.color = new Color(e.color.r, e.color.g, e.color.b, a);
            GUI.Label(r, e.text, style);
        }
        style.fontSize = baseSize;
        GUI.color = Color.white;
    }
}
