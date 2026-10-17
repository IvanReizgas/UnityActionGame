using UnityEngine;

// Shared construction for every character: root = physics + logic at the feet,
// "Body" child = animated sprite, plus a soft ground shadow.
public static class ActorBuilder
{
    public static GameObject Build(string name, Transform parent, Vector2 pos, string sheet, float footRadius,
        float mass, out CharacterAnimator anim)
    {
        var go = new GameObject(name);
        go.transform.SetParent(parent);
        go.transform.position = pos;

        // small, faint contact shadow right under the feet, plus a silhouette shadow cast on the ground
        var contact = Iso.Child(go.transform, "ContactShadow");
        contact.transform.localScale = Vector3.one * Mathf.Max(0.4f, footRadius * 3f);
        Iso.AddSprite(contact, SpriteFactory.Shadow, new Color(1f, 1f, 1f, 0.6f), Iso.GroundDecalOrder);

        var body = Iso.Child(go.transform, "Body");
        var sr = Iso.AddSprite(body, null, Color.white);
        anim = body.AddComponent<CharacterAnimator>();
        anim.Init(ArtLibrary.Character(sheet), sr);
        CastShadow.Attach(go.transform, sr);

        var rb = go.AddComponent<Rigidbody2D>();
        rb.gravityScale = 0f;
        rb.freezeRotation = true;
        rb.mass = mass;
        rb.interpolation = RigidbodyInterpolation2D.Interpolate;
        rb.collisionDetectionMode = CollisionDetectionMode2D.Continuous;

        // elliptical footprint so collisions match the isometric floor
        var col = go.AddComponent<CapsuleCollider2D>();
        col.direction = CapsuleDirection2D.Horizontal;
        col.size = new Vector2(footRadius * 2f, footRadius * 2f * Iso.YScale);

        go.AddComponent<Health>().Init(Team.Neutral, 1f, sr);
        return go;
    }
}
