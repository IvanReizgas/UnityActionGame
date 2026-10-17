using UnityEngine;

// Silhouette shadow: copies the character's current animation frame every frame, tints it dark,
// flattens it and lays it on the ground pointing away from the light (art spec: light from the
// upper left, toward the viewer, so shadows fall up and to the right).
public class CastShadow : MonoBehaviour
{
    // Tweak these to change every character's shadow.
    const float Angle = -55f;       // direction the shadow points (0 = straight up the screen, negative = to the right)
    const float Flatten = 0.45f;    // shadow length relative to the character's height
    const float Opacity = 0.3f;

    SpriteRenderer source, sr;

    public static void Attach(Transform actorRoot, SpriteRenderer source)
    {
        // rotate on the parent, squash on the child: squash first, then rotate (no shearing)
        var pivot = Iso.Child(actorRoot, "CastShadow");
        pivot.transform.localRotation = Quaternion.Euler(0, 0, Angle);
        var vis = Iso.Child(pivot.transform, "Sprite");
        vis.transform.localScale = new Vector3(1f, Flatten, 1f);

        var shadow = vis.AddComponent<CastShadow>();
        shadow.source = source;
        shadow.sr = Iso.AddSprite(vis, null, new Color(0, 0, 0, Opacity), Iso.GroundDecalOrder);
    }

    void LateUpdate()
    {
        sr.sprite = source.sprite;
        sr.flipX = source.flipX;
        // follow the character's transparency (e.g. enemies fading out when they die)
        sr.color = new Color(0f, 0f, 0f, Opacity * source.color.a);
    }
}
