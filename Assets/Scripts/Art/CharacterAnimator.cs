using System;
using UnityEngine;

// Plays 8-directional sprite animations from a CharacterSheet.
public class CharacterAnimator : MonoBehaviour
{
    public CharacterSheet Sheet { get; private set; }
    public int Dir { get; private set; }
    public Vector2 Facing => CharacterSheet.DirVector(Dir);
    public string Current => anim?.name;
    public bool OneShotPlaying => anim != null && !anim.loop && !finished;
    public SpriteRenderer Renderer => sr;
    [NonSerialized] public float Speed = 1f;
    [NonSerialized] public bool UseUnscaledTime;

    public event Action HitFrame;
    public event Action<string> Finished;

    SpriteRenderer sr;
    CharacterSheet.Anim anim;
    float time;
    int lastFrame = -1;
    bool finished;

    public void Init(CharacterSheet sheet, SpriteRenderer renderer)
    {
        Sheet = sheet;
        sr = renderer;
        Dir = 0;
        Play("idle", true);
    }

    public void SetFacing(Vector2 groundDir)
    {
        if (groundDir.sqrMagnitude > 0.0001f) Dir = CharacterSheet.DirIndex(groundDir);
    }

    public void SetDir(int dir) => Dir = (dir % 8 + 8) % 8;

    public void Play(string name, bool restart = false)
    {
        var next = Sheet.Get(name) ?? Sheet.Get("idle");
        if (next == null) return;
        if (next == anim && !restart) return;
        anim = next;
        time = 0f;
        lastFrame = -1;
        finished = false;
        Refresh();
    }

    void Update()
    {
        if (anim == null) return;
        time += (UseUnscaledTime ? Time.unscaledDeltaTime : Time.deltaTime) * Speed;
        Refresh();
    }

    void Refresh()
    {
        int frame = Mathf.FloorToInt(time * anim.fps);
        if (anim.loop) frame %= anim.frames;
        else if (frame >= anim.frames)
        {
            frame = anim.frames - 1;
            if (!finished)
            {
                finished = true;
                var name = anim.name;
                Finished?.Invoke(name);
            }
        }
        if (frame != lastFrame)
        {
            if (anim.hitFrame >= 0 && lastFrame < anim.hitFrame && frame >= anim.hitFrame) HitFrame?.Invoke();
            lastFrame = frame;
        }
        if (anim == null) return; // a Finished handler may have switched animation
        sr.sprite = CharacterSheet.Frame(anim, Dir, frame, out bool flip);
        sr.flipX = flip;
    }
}
