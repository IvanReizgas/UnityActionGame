using System.Collections;
using UnityEngine;

// Dev helper for automated visual checks. Launch the player with:
//   -screenshot <path>        capture a frame and quit
//   -region <id> [-entry <id>] start in another region
//   -talk <npc id>            open a conversation with that NPC first
//   -near <npc or enemy id>   stand next to it
//   -walk <dir>               hold a movement direction: n, ne, e, se, s, sw, w, nw
//   -dodge-at <seconds>       trigger a dodge and capture that many seconds into it
//   -attack-at <seconds>      swing the sword and capture that many seconds into the swing
public class ScreenshotMode : MonoBehaviour
{
    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
    static void Boot()
    {
        if (Arg("-screenshot") != null) new GameObject("ScreenshotMode").AddComponent<ScreenshotMode>();
    }

    static string Arg(string name, int offset = 1)
    {
        var args = System.Environment.GetCommandLineArgs();
        for (int i = 0; i < args.Length - offset; i++)
            if (args[i] == name) return args[i + offset];
        return null;
    }

    IEnumerator Start()
    {
        var gm = GameManager.Instance;
        yield return new WaitForSecondsRealtime(1f);

        var region = Arg("-region");
        if (region != null)
        {
            gm.Travel(region, Arg("-entry") ?? "from_forest");
            yield return new WaitForSecondsRealtime(1.5f);
        }

        var near = Arg("-near");
        if (near != null)
        {
            Transform t = null;
            foreach (var n in Npc.All) if (n.Def.id == near) t = n.transform;
            foreach (var e in Enemy.All) if (e.Def.id == near) t = e.transform;
            if (t) Player.Instance.Teleport((Vector2)t.position + new Vector2(0.45f, -0.3f));
            PixelCamera.Instance.Snap();
            yield return new WaitForSecondsRealtime(0.8f);
        }

        var talk = Arg("-talk");
        if (talk != null)
            foreach (var n in Npc.All)
                if (n.Def.id == talk)
                {
                    Player.Instance.Teleport((Vector2)n.transform.position + new Vector2(0.4f, -0.25f));
                    PixelCamera.Instance.Snap();
                    gm.StartDialogue(n);
                    break;
                }

        var walkDir = Arg("-walk");
        if (walkDir != null)
        {
            // direction names avoid number parsing: n, ne, e, se, s, sw, w, nw
            string[] names = { "s", "sw", "w", "nw", "n", "ne", "e", "se" };
            int idx = System.Array.IndexOf(names, walkDir.ToLowerInvariant());
            if (idx >= 0) Player.DebugMove = CharacterSheet.DirVector(idx);
            else Debug.LogWarning($"[screenshot] unknown -walk direction '{walkDir}'");
        }
        float delay = 2f;
        if (Arg("-dodge-at") != null)
        {
            // start a dodge, then capture this many seconds into it
            yield return new WaitForSecondsRealtime(1f);
            Player.DebugDodge = true;
            delay = float.Parse(Arg("-dodge-at"), System.Globalization.CultureInfo.InvariantCulture);
        }
        if (Arg("-attack-at") != null)
        {
            // swing the sword, then capture this many seconds into the swing
            yield return new WaitForSecondsRealtime(1f);
            Player.DebugAttack = true;
            delay = float.Parse(Arg("-attack-at"), System.Globalization.CultureInfo.InvariantCulture);
        }
        yield return new WaitForSecondsRealtime(delay);
        if (Arg("-report") != null)
        {
            // dev: log what the player is touching (for "stuck" bugs)
            var p = Player.Instance;
            Debug.Log($"[report] player at {p.transform.position}, velocity {p.GetComponent<Rigidbody2D>().linearVelocity}");
            Debug.Log($"[report] state={gm.State} timeScale={Time.timeScale} dead={p.Health.IsDead} stunned={p.Health.Stunned} anim={p.Anim.Current} region={gm.Region?.Id} debugMove={Player.DebugMove}");
            var contacts = new ContactPoint2D[16];
            int n = p.GetComponent<Rigidbody2D>().GetContacts(contacts);
            for (int i = 0; i < n; i++)
                Debug.Log($"[report] contact: {contacts[i].collider.name} ({contacts[i].collider.GetType().Name}) at {contacts[i].collider.transform.position}, point {contacts[i].point}, normal {contacts[i].normal}");
        }
        ScreenCapture.CaptureScreenshot(Arg("-screenshot"));
        yield return new WaitForSecondsRealtime(1f);
        Application.Quit();
    }
}
