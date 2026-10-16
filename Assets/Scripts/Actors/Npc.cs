using System.Collections.Generic;
using UnityEngine;

// A character you can talk to. Optionally wanders around its spawn point.
public class Npc : MonoBehaviour
{
    public static readonly List<Npc> All = new List<Npc>();

    const float WanderRadius = 1.6f, WalkSpeed = 0.9f;

    public NpcDef Def { get; private set; }
    public CharacterAnimator Anim { get; private set; }

    Rigidbody2D rb;
    Vector2 home, target;
    float timer;
    bool walking, talking;
    int restDir;

    public static Npc Spawn(NpcDef def, Vector2 pos, Transform parent)
    {
        var go = ActorBuilder.Build(def.id, parent, pos, def.sheet, 0.17f, 50f, out var anim);
        var n = go.AddComponent<Npc>();
        n.Def = def;
        n.Anim = anim;
        n.rb = go.GetComponent<Rigidbody2D>();
        n.rb.linearDamping = 10f;
        n.home = pos;
        n.timer = Random.Range(1f, 4f);
        n.restDir = Random.Range(0, 3) == 0 ? 1 : 0; // mostly face the camera
        anim.SetDir(n.restDir);
        anim.UseUnscaledTime = true; // keep breathing while the game is paused for dialogue
        return n;
    }

    void OnEnable() => All.Add(this);
    void OnDisable() => All.Remove(this);

    public void BeginTalk(Vector2 playerPos)
    {
        talking = true;
        walking = false;
        rb.linearVelocity = Vector2.zero;
        Anim.SetFacing(Iso.Direction(transform.position, playerPos));
        Anim.Play("idle");
    }

    public void EndTalk()
    {
        talking = false;
        timer = Random.Range(2f, 4f);
    }

    void FixedUpdate()
    {
        if (talking) return;
        timer -= Time.fixedDeltaTime;
        if (!Def.wander)
        {
            if (timer <= 0f)
            {
                // idle NPCs glance around now and then
                timer = Random.Range(3f, 7f);
                Anim.SetDir(Random.value < 0.6f ? restDir : Random.Range(0, 8));
            }
            return;
        }

        if (walking)
        {
            var to = Iso.ToGround(target - rb.position);
            if (to.magnitude < 0.08f || timer <= 0f || Region.Current.IsBlocked(rb.position + Iso.ToWorld(to.normalized * 0.3f)))
            {
                walking = false;
                timer = Random.Range(2f, 5f);
                rb.linearVelocity = Vector2.zero;
                Anim.Play("idle");
                return;
            }
            var dir = to.normalized;
            Anim.SetFacing(dir);
            rb.linearVelocity = Iso.ToWorld(dir * WalkSpeed);
        }
        else if (timer <= 0f)
        {
            walking = true;
            timer = 4f;
            target = home + Iso.ToWorld(Random.insideUnitCircle * WanderRadius);
            Anim.Play("walk");
        }
    }
}
