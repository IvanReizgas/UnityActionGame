using System;
using UnityEngine;

public enum Team { Player, Enemy, Neutral }

public class Health : MonoBehaviour
{
    public Team Side { get; private set; }
    public float Max { get; private set; }
    public float Current { get; private set; }
    public bool IsDead => Current <= 0f;
    public bool Stunned => stunTimer > 0f;

    [NonSerialized] public float InvulnerableTimer;
    [NonSerialized] public Color BaseColor = Color.white;
    [NonSerialized] public Color? Tint;
    [NonSerialized] public float TextHeight = 0.7f; // where damage numbers appear above the feet

    public event Action<float> Damaged;
    public event Action Died;

    SpriteRenderer body;
    Rigidbody2D rb;
    float flashTimer, stunTimer;

    public void Init(Team side, float max, SpriteRenderer bodyRenderer)
    {
        Side = side;
        Max = max;
        Current = max;
        body = bodyRenderer;
        rb = GetComponent<Rigidbody2D>();
    }

    public void SetMax(float max, bool refill)
    {
        Max = max;
        Current = refill ? max : Mathf.Min(Current, max);
    }

    public void Heal(float amount) => Current = Mathf.Min(Max, Current + amount);
    public void Revive() => Current = Max;

    // knockback is in ground space
    public void TakeDamage(float amount, Vector2 knockback)
    {
        if (IsDead || InvulnerableTimer > 0f) return;
        Current = Mathf.Max(0f, Current - amount);
        flashTimer = 0.1f;
        if (rb && knockback != Vector2.zero)
        {
            rb.linearVelocity = Iso.ToWorld(knockback) / Mathf.Max(1f, rb.mass * 0.5f);
            stunTimer = 0.18f;
        }
        FloatingText.Add(transform.position + Vector3.up * TextHeight, Mathf.CeilToInt(amount).ToString(),
            Side == Team.Player ? new Color(1f, 0.35f, 0.3f) : Color.white);
        Damaged?.Invoke(amount);
        if (IsDead) Died?.Invoke();
    }

    void Update()
    {
        flashTimer -= Time.deltaTime;
        stunTimer -= Time.deltaTime;
        InvulnerableTimer -= Time.deltaTime;
        if (body) body.color = flashTimer > 0f ? new Color(1f, 0.45f, 0.45f, BaseColor.a) : (Tint ?? BaseColor);
    }
}
