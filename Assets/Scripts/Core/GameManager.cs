using System.Collections;
using UnityEngine;

// Owns the session: camera, loading regions, dialogue mode, pause and death.
public class GameManager : MonoBehaviour
{
    public static GameManager Instance { get; private set; }

    public const string StartRegion = "forest", StartEntry = "start";

    public enum Mode { Playing, Dialogue, Paused, GameOver, Travelling }
    public Mode State { get; private set; } = Mode.Travelling;
    public Transform LevelRoot { get; private set; }
    public Region Region { get; private set; }
    public float Fade { get; private set; } = 1f;       // 1 = black
    public string Banner { get; private set; }
    public float BannerTimer { get; private set; }
    public float PlayTime { get; private set; }

    public DialogueRunner Dialogue { get; } = new DialogueRunner();
    public Npc DialogueNpc { get; private set; }
    // frame numbers used so one key press can't both open and advance/close a conversation
    public int DialogueStartFrame { get; private set; } = -1;
    public int DialogueEndFrame { get; private set; } = -1;

    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
    static void Boot()
    {
        if (FindAnyObjectByType<GameManager>() == null)
            new GameObject("GameManager").AddComponent<GameManager>();
    }

    void Awake()
    {
        Instance = this;
        if (!GetComponent<Hud>()) gameObject.AddComponent<Hud>();
    }

    void Start()
    {
        SetupCamera();
        WorldState.Reset();
        var player = Player.Create(Vector2.zero);
        PixelCamera.Instance.target = player.transform;
        StartCoroutine(LoadRegion(StartRegion, StartEntry, fadeOut: false));
    }

    void SetupCamera()
    {
        var cam = Camera.main;
        if (cam == null)
        {
            cam = new GameObject("Main Camera").AddComponent<Camera>();
            cam.tag = "MainCamera";
        }
        cam.orthographic = true;
        cam.clearFlags = CameraClearFlags.SolidColor;
        cam.backgroundColor = new Color(0.05f, 0.05f, 0.07f);
        // Isometric depth: things lower on screen are drawn in front.
        cam.transparencySortMode = TransparencySortMode.CustomAxis;
        cam.transparencySortAxis = Vector3.up;
        if (!cam.GetComponent<PixelCamera>()) cam.gameObject.AddComponent<PixelCamera>();
    }

    public void Travel(string region, string entry)
    {
        if (State != Mode.Playing) return;
        StartCoroutine(LoadRegion(region, entry, fadeOut: true));
    }

    IEnumerator LoadRegion(string id, string entry, bool fadeOut)
    {
        State = Mode.Travelling;
        if (fadeOut)
            for (Fade = 0f; Fade < 1f; Fade += Time.unscaledDeltaTime * 3f) yield return null;
        Fade = 1f;

        if (LevelRoot) Destroy(LevelRoot.gameObject);
        yield return null; // let the old region finish destroying
        LevelRoot = new GameObject("Region " + id).transform;
        FloatingText.Clear();
        Region = Region.Load(id, LevelRoot);
        if (Region != null)
        {
            Player.Instance.Teleport(Region.Entry(entry));
            PixelCamera.Instance.Snap();
            ShowBanner(Region.Name);
        }

        State = Mode.Playing;
        for (Fade = 1f; Fade > 0f; Fade -= Time.unscaledDeltaTime * 3f) yield return null;
        Fade = 0f;
    }

    public void StartDialogue(Npc npc)
    {
        if (State != Mode.Playing) return;
        DialogueNpc = npc;
        DialogueStartFrame = Time.frameCount;
        npc.BeginTalk(Player.Instance.transform.position);
        Player.Instance.Anim.SetFacing(Iso.Direction(Player.Instance.transform.position, npc.transform.position));
        Dialogue.Start(DialogueScript.Load(npc.Def.dialogue));
        if (Dialogue.Finished) { EndDialogue(); return; }
        State = Mode.Dialogue;
        Time.timeScale = 0f;
    }

    public void EndDialogue()
    {
        if (DialogueNpc) DialogueNpc.EndTalk();
        DialogueNpc = null;
        DialogueEndFrame = Time.frameCount;
        State = Mode.Playing;
        Time.timeScale = 1f;
    }

    void ShowBanner(string text)
    {
        Banner = text;
        BannerTimer = 3f;
    }

    public void OnPlayerDied()
    {
        State = Mode.GameOver;
        PixelCamera.Instance.Shake(0.15f);
    }

    public void Respawn()
    {
        var p = Player.Instance;
        p.AddGold(-p.Gold / 4);
        p.ResetForRespawn();
        StartCoroutine(LoadRegion(StartRegion, StartEntry, fadeOut: true));
    }

    public void SetPaused(bool paused)
    {
        if (paused && State != Mode.Playing) return;
        if (!paused && State != Mode.Paused) return;
        State = paused ? Mode.Paused : Mode.Playing;
        Time.timeScale = paused ? 0f : 1f;
    }

    void Update()
    {
        BannerTimer -= Time.unscaledDeltaTime;
        if (State == Mode.Playing) PlayTime += Time.deltaTime;
        FloatingText.Tick(Time.deltaTime);

        if (Input.GetKeyDown(KeyCode.Escape))
        {
            if (State == Mode.Playing) SetPaused(true);
            else if (State == Mode.Paused) SetPaused(false);
            else if (State == Mode.Dialogue) EndDialogue();
        }
        if (State == Mode.GameOver && Input.GetKeyDown(KeyCode.R)) Respawn();
    }
}
