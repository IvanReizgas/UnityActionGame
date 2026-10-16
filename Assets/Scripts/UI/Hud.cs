using UnityEngine;

// Immediate-mode HUD + dialogue box. Fine for prototyping; move to UI Toolkit before release.
public class Hud : MonoBehaviour
{
    const float CharsPerSecond = 45f;

    GUIStyle label, center, big, small, body, nameStyle, choice;
    float ui; // UI scale relative to 1080p

    // dialogue presentation
    string shownText;
    float typed;
    int selected;

    void Update()
    {
        var gm = GameManager.Instance;
        if (gm == null || gm.State != GameManager.Mode.Dialogue) return;
        if (Time.frameCount == gm.DialogueStartFrame) return;
        var d = gm.Dialogue;

        if (d.Text != shownText)
        {
            shownText = d.Text;
            typed = 0f;
            selected = 0;
        }
        typed += Time.unscaledDeltaTime * CharsPerSecond;
        bool fullyTyped = shownText == null || typed >= shownText.Length;

        bool confirm = Input.GetKeyDown(KeyCode.E) || Input.GetKeyDown(KeyCode.Space) || Input.GetKeyDown(KeyCode.Return);
        if (!fullyTyped)
        {
            if (confirm || Input.GetMouseButtonDown(0)) typed = shownText.Length;
            return;
        }

        if (d.Choices.Count > 0)
        {
            if (Input.GetKeyDown(KeyCode.W) || Input.GetKeyDown(KeyCode.UpArrow)) selected = (selected + d.Choices.Count - 1) % d.Choices.Count;
            if (Input.GetKeyDown(KeyCode.S) || Input.GetKeyDown(KeyCode.DownArrow)) selected = (selected + 1) % d.Choices.Count;
            for (int i = 0; i < d.Choices.Count && i < 9; i++)
                if (Input.GetKeyDown(KeyCode.Alpha1 + i)) { Choose(i); return; }
            if (confirm) Choose(selected);
        }
        else if (confirm || Input.GetMouseButtonDown(0))
        {
            d.Continue();
            if (d.Finished) gm.EndDialogue();
        }
    }

    void Choose(int i)
    {
        var gm = GameManager.Instance;
        gm.Dialogue.Choose(i);
        selected = 0;
        if (gm.Dialogue.Finished) gm.EndDialogue();
    }

    void OnGUI()
    {
        ui = Screen.height / 1080f;
        EnsureStyles();
        var gm = GameManager.Instance;
        var player = Player.Instance;
        var cam = Camera.main;
        if (gm == null || player == null || cam == null) return;

        if (gm.State != GameManager.Mode.Dialogue)
        {
            DrawEnemyBars(cam);
            FloatingText.Draw(cam, center);
            DrawInteractPrompt(cam, player);
        }

        // stats, top-left
        float x = 24 * ui, y = 24 * ui, w = 360 * ui, h = 26 * ui;
        Bar(x, y, w, h, player.Health.Current / player.Health.Max, new Color(0.8f, 0.2f, 0.22f),
            $"HP {Mathf.CeilToInt(player.Health.Current)} / {Mathf.CeilToInt(player.Health.Max)}");
        Bar(x, y + h + 8 * ui, w, h * 0.45f, player.Xp / (float)player.XpToNext, new Color(0.95f, 0.8f, 0.25f), "");
        Shadowed(new Rect(x, y + h * 1.6f + 14 * ui, 800 * ui, 40 * ui),
            $"{Player.DisplayName}  ·  Level {player.Level}    Gold {player.Gold}    Potions {player.Potions} [Q]", label);
        Bar(x, y + h * 2.9f + 18 * ui, w * 0.25f, h * 0.3f, player.RollReady, new Color(0.7f, 0.9f, 1f), "");

        if (gm.BannerTimer > 0f && !string.IsNullOrEmpty(gm.Banner))
        {
            GUI.color = new Color(1, 1, 1, Mathf.Clamp01(gm.BannerTimer));
            Shadowed(new Rect(0, Screen.height * 0.16f, Screen.width, 120 * ui), gm.Banner, big);
            GUI.color = Color.white;
        }

        if (gm.PlayTime < 15f && gm.State == GameManager.Mode.Playing)
            Shadowed(new Rect(0, Screen.height - 70 * ui, Screen.width, 40 * ui),
                "WASD move  ·  LMB / J attack  ·  Space roll  ·  E talk  ·  Q potion  ·  Esc pause", center);

        switch (gm.State)
        {
            case GameManager.Mode.Dialogue: DrawDialogue(gm); break;
            case GameManager.Mode.Paused: PauseMenu(gm); break;
            case GameManager.Mode.GameOver: GameOver(gm); break;
        }

        if (gm.Fade > 0f)
        {
            GUI.color = new Color(0, 0, 0, gm.Fade);
            GUI.DrawTexture(new Rect(0, 0, Screen.width, Screen.height), Texture2D.whiteTexture);
            GUI.color = Color.white;
        }
    }

    void DrawInteractPrompt(Camera cam, Player player)
    {
        var npc = player.InteractTarget;
        if (npc == null || GameManager.Instance.State != GameManager.Mode.Playing) return;
        var sp = cam.WorldToScreenPoint(npc.transform.position + Vector3.up * 0.95f);
        var r = new Rect(sp.x - 200 * ui, Screen.height - sp.y - 30 * ui, 400 * ui, 40 * ui);
        Shadowed(r, $"[E] Talk to {npc.Def.name}", center);
    }

    void DrawDialogue(GameManager gm)
    {
        var d = gm.Dialogue;
        float pw = Mathf.Min(1400 * ui, Screen.width - 40 * ui);
        float ph = (300 + Mathf.Max(0, d.Choices.Count - 3) * 34) * ui;
        var panel = new Rect((Screen.width - pw) / 2, Screen.height - ph - 30 * ui, pw, ph);

        GUI.color = new Color(0.06f, 0.05f, 0.08f, 0.92f);
        GUI.DrawTexture(panel, Texture2D.whiteTexture);
        GUI.color = new Color(0.75f, 0.62f, 0.38f);
        DrawFrame(panel, 3 * ui);
        GUI.color = Color.white;

        // who is speaking
        string speakerName = null, portrait = null;
        if (d.Speaker == "you" || d.Speaker == "player")
        {
            speakerName = Player.DisplayName;
            portrait = "warrior";
        }
        else if (!string.IsNullOrEmpty(d.Speaker))
        {
            var def = GameData.Npc(d.Speaker);
            speakerName = def != null ? def.name : d.Speaker;
            portrait = def?.portrait;
        }

        float pad = 24 * ui;
        float textX = panel.x + pad;
        var tex = ArtLibrary.Portrait(portrait);
        if (tex)
        {
            float size = 252 * ui;
            var pr = new Rect(panel.x + pad, panel.y + pad, size, size);
            GUI.color = new Color(0.16f, 0.14f, 0.2f);
            GUI.DrawTexture(pr, Texture2D.whiteTexture);
            GUI.color = Color.white;
            GUI.DrawTexture(pr, tex, ScaleMode.ScaleToFit);
            GUI.color = new Color(0.75f, 0.62f, 0.38f);
            DrawFrame(pr, 2 * ui);
            GUI.color = Color.white;
            textX = pr.xMax + pad;
        }
        float textW = panel.xMax - pad - textX;
        float ty = panel.y + pad;
        if (!string.IsNullOrEmpty(speakerName))
        {
            GUI.Label(new Rect(textX, ty, textW, 40 * ui), speakerName, nameStyle);
            ty += 44 * ui;
        }

        string text = shownText ?? "";
        int n = Mathf.Clamp(Mathf.FloorToInt(typed), 0, text.Length);
        GUI.Label(new Rect(textX, ty, textW, 120 * ui), text.Substring(0, n), body);
        ty += 110 * ui;

        bool fullyTyped = n >= text.Length;
        if (fullyTyped && d.Choices.Count > 0)
        {
            for (int i = 0; i < d.Choices.Count; i++)
            {
                var r = new Rect(textX, ty + i * 34 * ui, textW, 34 * ui);
                bool hover = r.Contains(Event.current.mousePosition);
                if (hover) selected = i;
                choice.normal.textColor = i == selected ? new Color(1f, 0.85f, 0.45f) : new Color(0.85f, 0.85f, 0.85f);
                GUI.Label(r, $"{(i == selected ? "▸" : " ")} {i + 1}. {d.Choices[i].text}", choice);
                if (hover && Event.current.type == EventType.MouseDown && Event.current.button == 0)
                {
                    Event.current.Use();
                    Choose(i);
                    return;
                }
            }
        }
        else if (fullyTyped)
        {
            float blink = Mathf.Repeat(Time.unscaledTime * 2f, 1f) < 0.6f ? 1f : 0.3f;
            GUI.color = new Color(1, 1, 1, blink);
            GUI.Label(new Rect(panel.xMax - 220 * ui, panel.yMax - 46 * ui, 200 * ui, 36 * ui), "[E] ▸", small);
            GUI.color = Color.white;
        }
    }

    void DrawEnemyBars(Camera cam)
    {
        foreach (var e in Enemy.All)
        {
            if (e.Health.IsDead || e.Health.Current >= e.Health.Max) continue;
            var sp = cam.WorldToScreenPoint(e.transform.position + Vector3.up * e.BarHeight);
            float bw = 70 * ui, bh = 8 * ui;
            Bar(sp.x - bw / 2, Screen.height - sp.y, bw, bh, e.Health.Current / e.Health.Max, new Color(0.85f, 0.2f, 0.25f), "");
        }
    }

    void PauseMenu(GameManager gm)
    {
        Dim();
        float bw = 320 * ui, bh = 60 * ui, cx = (Screen.width - bw) / 2, cy = Screen.height * 0.4f;
        Shadowed(new Rect(0, cy - 140 * ui, Screen.width, 100 * ui), "Paused", big);
        if (GUI.Button(new Rect(cx, cy, bw, bh), "Resume")) gm.SetPaused(false);
        if (GUI.Button(new Rect(cx, cy + bh + 16 * ui, bw, bh), "Quit")) Application.Quit();
    }

    void GameOver(GameManager gm)
    {
        Dim();
        float bw = 360 * ui, bh = 60 * ui, cx = (Screen.width - bw) / 2, cy = Screen.height * 0.5f;
        Shadowed(new Rect(0, cy - 200 * ui, Screen.width, 100 * ui), "You have fallen", big);
        Shadowed(new Rect(0, cy - 100 * ui, Screen.width, 50 * ui), "You will wake in Greenhollow (lose 25% gold)", center);
        if (GUI.Button(new Rect(cx, cy, bw, bh), "Rise again  [R]")) gm.Respawn();
    }

    void Dim()
    {
        GUI.color = new Color(0, 0, 0, 0.6f);
        GUI.DrawTexture(new Rect(0, 0, Screen.width, Screen.height), Texture2D.whiteTexture);
        GUI.color = Color.white;
    }

    static void DrawFrame(Rect r, float t)
    {
        GUI.DrawTexture(new Rect(r.x, r.y, r.width, t), Texture2D.whiteTexture);
        GUI.DrawTexture(new Rect(r.x, r.yMax - t, r.width, t), Texture2D.whiteTexture);
        GUI.DrawTexture(new Rect(r.x, r.y, t, r.height), Texture2D.whiteTexture);
        GUI.DrawTexture(new Rect(r.xMax - t, r.y, t, r.height), Texture2D.whiteTexture);
    }

    void Shadowed(Rect r, string text, GUIStyle style)
    {
        var c = GUI.color;
        GUI.color = new Color(0, 0, 0, c.a * 0.8f);
        GUI.Label(new Rect(r.x + 2 * ui, r.y + 2 * ui, r.width, r.height), text, style);
        GUI.color = c;
        GUI.Label(r, text, style);
    }

    void Bar(float x, float y, float w, float h, float fill, Color color, string text)
    {
        GUI.color = new Color(0, 0, 0, 0.7f);
        GUI.DrawTexture(new Rect(x - 2, y - 2, w + 4, h + 4), Texture2D.whiteTexture);
        GUI.color = color;
        GUI.DrawTexture(new Rect(x, y, w * Mathf.Clamp01(fill), h), Texture2D.whiteTexture);
        GUI.color = Color.white;
        if (!string.IsNullOrEmpty(text)) GUI.Label(new Rect(x + 8 * ui, y, w, h), text, small);
    }

    void EnsureStyles()
    {
        if (label == null)
        {
            label = new GUIStyle(GUI.skin.label) { fontStyle = FontStyle.Bold };
            center = new GUIStyle(label) { alignment = TextAnchor.MiddleCenter };
            big = new GUIStyle(center);
            small = new GUIStyle(label) { alignment = TextAnchor.MiddleLeft };
            body = new GUIStyle(GUI.skin.label) { wordWrap = true, alignment = TextAnchor.UpperLeft };
            nameStyle = new GUIStyle(label);
            nameStyle.normal.textColor = new Color(0.95f, 0.78f, 0.45f);
            choice = new GUIStyle(GUI.skin.label) { alignment = TextAnchor.MiddleLeft };
        }
        label.fontSize = Mathf.RoundToInt(24 * ui);
        center.fontSize = Mathf.RoundToInt(24 * ui);
        big.fontSize = Mathf.RoundToInt(64 * ui);
        small.fontSize = Mathf.RoundToInt(18 * ui);
        body.fontSize = Mathf.RoundToInt(28 * ui);
        nameStyle.fontSize = Mathf.RoundToInt(30 * ui);
        choice.fontSize = Mathf.RoundToInt(26 * ui);
        GUI.skin.button.fontSize = Mathf.RoundToInt(26 * ui);
    }
}
