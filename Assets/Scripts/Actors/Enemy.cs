using System.Collections.Generic;
using UnityEngine;

// Hostile creature: idles/wanders near home, chases the player when close, attacks in melee.
public class Enemy : MonoBehaviour
{
    public static readonly List<Enemy> All = new List<Enemy>();

    public EnemyDef Def { get; private set; }
    public Health Health { get; private set; }
    public float BarHeight => 0.75f;

    CharacterAnimator anim;
    Rigidbody2D rb;
    Vector2 home, wanderTarget;
    bool aggro, attacking, wandering;
    float attackCd, wanderTimer, deathTimer;

    public static Enemy Spawn(EnemyDef def, Vector2 pos, Transform parent)
    {
        var go = ActorBuilder.Build(def.id, parent, pos, def.sheet, def.footRadius, 2f, out var anim);
        var e = go.AddComponent<Enemy>();
        e.Def = def;
        e.anim = anim;
        e.rb = go.GetComponent<Rigidbody2D>();
        e.Health = go.GetComponent<Health>();
        e.Health.Init(Team.Enemy, def.hp, anim.Renderer);
        e.Health.TextHeight = 0.6f;
        e.Health.Died += e.OnDied;
        e.Health.Damaged += _ => e.aggro = true;
        e.home = pos;
        e.wanderTimer = Random.Range(1f, 4f);
        anim.SetDir(Random.Range(0, 8));
        anim.HitFrame += e.OnAttackHit;
        anim.Finished += n => { if (n == "attack") e.attacking = false; };
        return e;
    }

    void OnEnable() => All.Add(this);
    void OnDisable() => All.Remove(this);

    void FixedUpdate()
    {
        float dt = Time.fixedDeltaTime;
        if (Health.IsDead)
        {
            deathTimer += dt;
            Health.BaseColor = new Color(1, 1, 1, Mathf.Clamp01(1f - deathTimer / 0.8f));
            rb.linearVelocity = Vector2.zero;
            if (deathTimer > 0.8f) Destroy(gameObject);
            return;
        }
        if (Health.Stunned) return;

        attackCd -= dt;
        var player = Player.Instance;
        bool playerAlive = player && !player.Health.IsDead;
        Vector2 pos = rb.position;
        float dist = playerAlive ? Iso.Distance(pos, player.transform.position) : float.MaxValue;

        if (!aggro && dist < Def.aggroRange) aggro = true;
        if (aggro && (dist > Def.aggroRange * 2.2f || Iso.Distance(pos, home) > 9f)) aggro = false;

        if (attacking)
        {
            rb.linearVelocity = Vector2.MoveTowards(rb.linearVelocity, Vector2.zero, 20f * dt);
            return;
        }

        if (aggro)
        {
            var dir = Iso.Direction(pos, player.transform.position);
            anim.SetFacing(dir);
            if (dist <= Def.attackRange)
            {
                rb.linearVelocity = Vector2.zero;
                if (attackCd <= 0f)
                {
                    attacking = true;
                    attackCd = Random.Range(1.0f, 1.6f);
                    anim.Play("attack", true);
                }
                else anim.Play("idle");
            }
            else
            {
                rb.linearVelocity = Iso.ToWorld(dir * Def.speed);
                anim.Play("walk");
            }
            return;
        }

        // idle / wander around home
        wanderTimer -= dt;
        if (wandering)
        {
            var to = Iso.ToGround(wanderTarget - pos);
            if (to.magnitude < 0.1f || wanderTimer <= 0f)
            {
                wandering = false;
                wanderTimer = Random.Range(2f, 5f);
                rb.linearVelocity = Vector2.zero;
                anim.Play("idle");
            }
            else
            {
                anim.SetFacing(to);
                rb.linearVelocity = Iso.ToWorld(to.normalized * Def.speed * 0.35f);
            }
        }
        else
        {
            rb.linearVelocity = Vector2.zero;
            if (wanderTimer <= 0f)
            {
                wandering = true;
                wanderTimer = 4f;
                wanderTarget = home + Iso.ToWorld(Random.insideUnitCircle * 1.5f);
                anim.Play("walk");
            }
        }
    }

    void OnAttackHit()
    {
        var player = Player.Instance;
        if (!player || player.Health.IsDead || Health.IsDead) return;
        float d = Iso.Distance(transform.position, player.transform.position);
        if (d <= Def.attackRange * 1.35f)
            player.Health.TakeDamage(Def.damage * Random.Range(0.85f, 1.15f),
                Iso.Direction(transform.position, player.transform.position) * 3f);
    }

    void OnDied()
    {
        Vector2 pos = transform.position;
        GetComponent<Collider2D>().enabled = false;
        attacking = false;
        anim.Play("idle", true);
        if (Player.Instance) Player.Instance.AddXp(Def.xp);
        WorldState.Add("killed_" + Def.id, 1);
        int coins = Random.Range(0, 3);
        for (int i = 0; i < coins; i++) Pickup.Spawn(PickupKind.Gold, pos, Mathf.Max(1, Def.gold + Random.Range(-1, 2)));
        if (Random.value < 0.15f) Pickup.Spawn(PickupKind.Potion, pos, 1);
    }
}
