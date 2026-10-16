using UnityEngine;

// Walking onto this cell travels to another region.
public class ExitTrigger : MonoBehaviour
{
    string region, entry;

    public static void Create(Transform parent, Vector2 pos, string region, string entry)
    {
        var go = Iso.Child(parent, $"Exit to {region}");
        go.transform.position = pos;
        var col = go.AddComponent<PolygonCollider2D>();
        col.isTrigger = true;
        col.points = new[]
        {
            new Vector2(0.45f, 0), new Vector2(0, 0.22f), new Vector2(-0.45f, 0), new Vector2(0, -0.22f),
        };
        var e = go.AddComponent<ExitTrigger>();
        e.region = region;
        e.entry = entry;
    }

    void OnTriggerEnter2D(Collider2D other)
    {
        if (other.GetComponent<Player>()) GameManager.Instance.Travel(region, entry);
    }
}
