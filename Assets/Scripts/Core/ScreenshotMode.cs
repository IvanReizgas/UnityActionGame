using System.Collections;
using UnityEngine;

// Dev helper for automated visual checks. Launch the player with:
//   -screenshot <path>        capture a frame and quit
//   -region <id> [-entry <id>] start in another region
//   -talk <npc id>            open a conversation with that NPC first
//   -near <npc or enemy id>   stand next to it
//   -walk <dx> <dy>           hold a movement direction for a moment before the capture
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

        yield return new WaitForSecondsRealtime(2f);
        ScreenCapture.CaptureScreenshot(Arg("-screenshot"));
        yield return new WaitForSecondsRealtime(1f);
        Application.Quit();
    }
}
