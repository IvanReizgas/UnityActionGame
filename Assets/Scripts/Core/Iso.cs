using UnityEngine;

// Isometric helpers. "World" is Unity's 2D world (what the camera sees).
// "Ground" is the same plane un-squashed, so distances and directions are uniform
// in every direction. Gameplay math (speed, aim, ranges) happens in ground space.
public static class Iso
{
    public const float YScale = 0.5f; // 2:1 isometric diamonds

    public static Vector2 ToWorld(Vector2 ground) => new Vector2(ground.x, ground.y * YScale);
    public static Vector2 ToGround(Vector2 world) => new Vector2(world.x, world.y / YScale);
    public static float Distance(Vector2 worldA, Vector2 worldB) => ToGround(worldB - worldA).magnitude;
    public static Vector2 Direction(Vector2 worldFrom, Vector2 worldTo)
    {
        var g = ToGround(worldTo - worldFrom);
        return g.sqrMagnitude > 0.0001f ? g.normalized : Vector2.zero;
    }
    public static float Angle(Vector2 groundDir) => Mathf.Atan2(groundDir.y, groundDir.x) * Mathf.Rad2Deg;

    // Upright sprites sort by their feet; all share this order so they interleave with walls by Y.
    public const int WorldOrder = 0;
    public const int FloorOrder = -100;
    public const int GroundDecalOrder = -50;
    public const int FxOrder = 50;

    public static SpriteRenderer AddSprite(GameObject go, Sprite sprite, Color color, int order = WorldOrder)
    {
        var sr = go.AddComponent<SpriteRenderer>();
        sr.sprite = sprite;
        sr.color = color;
        sr.sortingOrder = order;
        sr.spriteSortPoint = SpriteSortPoint.Pivot;
        return sr;
    }

    public static GameObject Child(Transform parent, string name, Vector2 localPos = default)
    {
        var go = new GameObject(name);
        go.transform.SetParent(parent, false);
        go.transform.localPosition = localPos;
        return go;
    }
}
