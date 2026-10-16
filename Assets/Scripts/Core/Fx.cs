using UnityEngine;

// Short-lived fading sprite effect (slashes, hit sparks, dodge afterimages).
public class Fx : MonoBehaviour
{
    SpriteRenderer sr;
    Color color;
    Vector3 baseScale;
    float life, t, grow;

    // onGround: the sprite is drawn lying flat on the isometric floor (rotated, then squashed).
    public static Fx Spawn(Sprite sprite, Vector2 pos, float groundAngle, float scale, Color color,
        float life, float grow = 0f, bool onGround = false, int order = Iso.FxOrder, bool flipX = false)
    {
        var root = new GameObject("Fx");
        root.transform.SetParent(GameManager.Instance.LevelRoot);
        root.transform.position = pos;
        if (onGround) root.transform.localScale = new Vector3(1f, Iso.YScale, 1f);

        var vis = Iso.Child(root.transform, "Sprite");
        vis.transform.localRotation = Quaternion.Euler(0, 0, groundAngle);
        vis.transform.localScale = Vector3.one * scale;
        var fx = root.AddComponent<Fx>();
        fx.sr = Iso.AddSprite(vis, sprite, color, order);
        fx.sr.flipX = flipX;
        fx.color = color;
        fx.baseScale = vis.transform.localScale;
        fx.life = life;
        fx.grow = grow;
        return fx;
    }

    public static void Burst(Vector2 pos, Color color, float size = 1f) =>
        Spawn(SpriteFactory.Orb, pos + new Vector2(0, 0.2f * size), 0, 1.2f * size, color, 0.25f, grow: 1.5f);

    void Update()
    {
        t += Time.deltaTime;
        float k = t / life;
        sr.color = new Color(color.r, color.g, color.b, color.a * (1f - k));
        sr.transform.localScale = baseScale * (1f + grow * k);
        if (t >= life) Destroy(gameObject);
    }
}
