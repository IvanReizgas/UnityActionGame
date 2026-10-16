using UnityEngine;

// The protagonist: a human warrior. 8-way movement, sword attacks, dodge roll, talking to NPCs.
public class Player : MonoBehaviour
{
    public static Player Instance { get; private set; }

    public const string DisplayName = "Aldric";
    const float MoveSpeed = 2.6f;          // ground units / second
    const float RollSpeed = 4.5f, RollDuration = 0.4f, RollCooldown = 0.7f; // slide: ~1.8 ground units
    const float AttackRange = 0.85f, AttackArc = 75f, AttackMoveFactor = 0.2f;
    const float InteractRange = 1.1f;
    const int MaxPotions = 5;

    public Health Health { get; private set; }
    public CharacterAnimator Anim { get; private set; }
    public int Level { get; private set; } = 1;
    public int Xp { get; private set; }
    public int Gold { get; private set; }
    public int Potions { get; private set; } = 2;
    public int XpToNext => 20 + (Level - 1) * 15 + (Level - 1) * (Level - 1) * 5;
    public float AttackDamage => 6f + Level * 1.5f;
    public float RollReady => 1f - Mathf.Clamp01(rollCd / RollCooldown);
    public Npc InteractTarget { get; private set; }

    // Dev/test hooks (used by ScreenshotMode): fake movement input and a dodge request.
    public static Vector2? DebugMove;
    public static bool DebugDodge;

    Rigidbody2D rb;
    Vector2 move;               // ground space
    float rollTimer, rollCd, afterimageTimer;
    Vector2 rollDir;
    bool attacking;

    public static Player Create(Vector2 pos)
    {
        var go = ActorBuilder.Build("Player", null, pos, "warrior", 0.17f, 1f, out var anim);
        var p = go.AddComponent<Player>();
        p.rb = go.GetComponent<Rigidbody2D>();
        p.Anim = anim;
        p.Health = go.GetComponent<Health>();
        p.Health.Init(Team.Player, 40f, anim.Renderer);
        p.Health.Damaged += p.OnDamaged;
        p.Health.Died += p.OnDied;
        anim.HitFrame += p.OnAttackHit;
        anim.Finished += name => { if (name == "attack") p.attacking = false; };
        Instance = p;
        return p;
    }

    void OnDestroy()
    {
        if (Instance == this) Instance = null;
    }

    public void Teleport(Vector2 pos)
    {
        rb.position = pos;
        transform.position = pos;
        rb.linearVelocity = Vector2.zero;
    }

    public void ResetForRespawn()
    {
        Health.Revive();
        Health.Tint = null;
        attacking = false;
        Anim.Play("idle", true);
    }

    void Update()
    {
        move = Vector2.zero;
        var gm = GameManager.Instance;
        if (Health.IsDead || gm.State != GameManager.Mode.Playing)
        {
            InteractTarget = null;
            if (!attacking && !Health.IsDead) Anim.Play("idle");
            return;
        }

        float dt = Time.deltaTime;
        rollTimer -= dt;
        rollCd -= dt;

        var input = new Vector2(Input.GetAxisRaw("Horizontal"), Input.GetAxisRaw("Vertical"));
        if (DebugMove.HasValue) input = DebugMove.Value;
        move = input.sqrMagnitude > 1f ? input.normalized : input;

        InteractTarget = FindInteractTarget();
        if (rollTimer <= 0f) Anim.Speed = 1f;

        if (rollTimer > 0f)
        {
            afterimageTimer -= dt;
            if (afterimageTimer <= 0f)
            {
                afterimageTimer = 0.05f;
                var sr = Anim.Renderer;
                Fx.Spawn(sr.sprite, transform.position, 0, 1f, new Color(0.7f, 0.85f, 1f, 0.45f), 0.2f,
                    order: Iso.WorldOrder, flipX: sr.flipX);
            }
            return;
        }

        if (!attacking)
        {
            if (Input.GetMouseButtonDown(0)) Attack(MouseDirection());
            else if (Input.GetKeyDown(KeyCode.J)) Attack(move != Vector2.zero ? move : Anim.Facing);
            else if ((Input.GetKeyDown(KeyCode.Space) || DebugDodge) && rollCd <= 0f) { DebugDodge = false; Roll(); return; } // don't let the walk/idle code below override the dodge
        }

        if (Input.GetKeyDown(KeyCode.E) && InteractTarget != null && Time.frameCount != gm.DialogueEndFrame) gm.StartDialogue(InteractTarget);
        if (Input.GetKeyDown(KeyCode.Q)) DrinkPotion();

        if (!attacking)
        {
            if (move != Vector2.zero)
            {
                Anim.SetFacing(move);
                Anim.Play("walk");
            }
            else Anim.Play("idle");
        }
    }

    void FixedUpdate()
    {
        if (Health.IsDead) { rb.linearVelocity = Vector2.zero; return; }
        if (rollTimer > 0f) { rb.linearVelocity = Iso.ToWorld(rollDir * RollSpeed); return; }
        if (Health.Stunned) return;
        float speed = attacking ? MoveSpeed * AttackMoveFactor : MoveSpeed;
        rb.linearVelocity = Iso.ToWorld(move * speed);
    }

    Vector2 MouseDirection()
    {
        Vector2 mouse = Camera.main.ScreenToWorldPoint(Input.mousePosition);
        var d = Iso.Direction(transform.position, mouse);
        return d != Vector2.zero ? d : Anim.Facing;
    }

    void Attack(Vector2 dir)
    {
        Anim.SetFacing(dir);
        Anim.Play("attack", true);
        attacking = true;
    }

    void OnAttackHit()
    {
        var facing = Anim.Facing;
        Vector2 pos = transform.position;
        Fx.Spawn(SpriteFactory.Arc, pos + Iso.ToWorld(facing * 0.25f), Iso.Angle(facing), 1.6f,
            new Color(1f, 1f, 1f, 0.8f), 0.12f, onGround: true);
        foreach (var e in Enemy.All.ToArray())
        {
            if (e.Health.IsDead) continue;
            float d = Iso.Distance(pos, e.transform.position);
            if (d > AttackRange + e.Def.footRadius) continue;
            var to = Iso.Direction(pos, e.transform.position);
            if (d > 0.3f && Vector2.Angle(facing, to) > AttackArc) continue;
            e.Health.TakeDamage(AttackDamage * Random.Range(0.85f, 1.15f), facing * 4f);
        }
    }

    void Roll()
    {
        rollDir = move != Vector2.zero ? move.normalized : Anim.Facing;
        Anim.SetFacing(rollDir);
        // Use a dedicated "dodge" animation when the sheet has one (dodge.png), stretched to fit the roll.
        var dodge = Anim.Sheet.Get("dodge");
        if (dodge != null)
        {
            Anim.Play("dodge", true);
            Anim.Speed = dodge.Duration / RollDuration;
        }
        else Anim.Play("walk");
        rollTimer = RollDuration;
        rollCd = RollCooldown;
        Health.InvulnerableTimer = RollDuration + 0.05f;
    }

    Npc FindInteractTarget()
    {
        Npc best = null;
        float bestD = InteractRange;
        foreach (var n in Npc.All)
        {
            float d = Iso.Distance(transform.position, n.transform.position);
            if (d < bestD) { bestD = d; best = n; }
        }
        return best;
    }

    void DrinkPotion()
    {
        if (Potions <= 0 || Health.Current >= Health.Max) return;
        Potions--;
        float amount = Health.Max * 0.5f;
        Health.Heal(amount);
        FloatingText.Add(transform.position + Vector3.up * 0.8f, "+" + Mathf.RoundToInt(amount), new Color(0.4f, 1f, 0.4f));
    }

    public void Collect(PickupKind kind, int amount)
    {
        if (kind == PickupKind.Gold) AddGold(amount);
        else if (Potions < MaxPotions) AddPotions(1);
        else Health.Heal(Health.Max * 0.25f);
    }

    public void AddGold(int amount)
    {
        Gold = Mathf.Max(0, Gold + amount);
        if (amount != 0)
            FloatingText.Add(transform.position + Vector3.up * 0.8f, (amount > 0 ? "+" : "") + amount + " gold",
                new Color(1f, 0.85f, 0.25f), 0.8f);
    }

    public void AddPotions(int amount)
    {
        Potions = Mathf.Clamp(Potions + amount, 0, MaxPotions);
        if (amount > 0)
            FloatingText.Add(transform.position + Vector3.up * 0.8f, $"+{amount} potion", new Color(1f, 0.4f, 0.45f), 0.8f);
    }

    public void AddXp(int amount)
    {
        Xp += amount;
        while (Xp >= XpToNext)
        {
            Xp -= XpToNext;
            Level++;
            Health.SetMax(Health.Max + 8f, refill: true);
            FloatingText.Add(transform.position + Vector3.up * 1f, "LEVEL UP!", new Color(1f, 0.9f, 0.3f), 1.5f);
            Fx.Burst(transform.position, new Color(1f, 0.9f, 0.3f), 2f);
        }
    }

    void OnDamaged(float amount)
    {
        Health.InvulnerableTimer = 0.5f;
        PixelCamera.Instance.Shake(0.06f);
    }

    void OnDied()
    {
        attacking = false;
        Health.Tint = new Color(0.45f, 0.45f, 0.5f);
        Anim.Play("idle", true);
        GameManager.Instance.OnPlayerDied();
    }
}
