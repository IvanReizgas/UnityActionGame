using UnityEngine;

// Static scenery (trees, rocks, houses). Tall props turn see-through when the player is behind them.
public class Prop : MonoBehaviour
{
    SpriteRenderer sr;
    Color color;
    float alpha = 1f;
    bool fade;

    public static Prop Create(PropDef def, Vector2 pos, Transform parent, Color ambient)
    {
        var go = Iso.Child(parent, def.name);
        go.transform.position = pos;
        var p = go.AddComponent<Prop>();
        p.color = ambient;
        p.fade = def.fade;
        p.sr = Iso.AddSprite(go, def.sprite, ambient);

        switch (def.colliderType)
        {
            case "ellipse":
                var cap = go.AddComponent<CapsuleCollider2D>();
                cap.direction = CapsuleDirection2D.Horizontal;
                cap.size = new Vector2(def.radius * 2f, def.radius * 2f * Iso.YScale);
                break;
            case "diamond":
                var poly = go.AddComponent<PolygonCollider2D>();
                poly.points = new[]
                {
                    new Vector2(def.halfWidth, 0), new Vector2(0, def.halfHeight),
                    new Vector2(-def.halfWidth, 0), new Vector2(0, -def.halfHeight),
                };
                break;
        }
        if (!p.fade) p.enabled = false;
        return p;
    }

    void LateUpdate()
    {
        var player = Player.Instance;
        float target = 1f;
        if (player)
        {
            Vector2 pp = player.transform.position + Vector3.up * 0.3f;
            if (player.transform.position.y > transform.position.y && sr.bounds.Contains(new Vector3(pp.x, pp.y, sr.bounds.center.z)))
                target = 0.45f;
        }
        if (Mathf.Approximately(alpha, target)) return;
        alpha = Mathf.MoveTowards(alpha, target, Time.deltaTime * 4f);
        sr.color = new Color(color.r, color.g, color.b, alpha);
    }
}
