using UnityEngine;

public enum PickupKind { Gold, Potion }

public class Pickup : MonoBehaviour
{
    PickupKind kind;
    int amount;
    Transform vis;
    float phase;

    public static void Spawn(PickupKind kind, Vector2 pos, int amount)
    {
        var go = new GameObject(kind.ToString());
        go.transform.SetParent(GameManager.Instance.LevelRoot);
        go.transform.position = pos + Iso.ToWorld(Random.insideUnitCircle * 0.4f);

        var p = go.AddComponent<Pickup>();
        p.kind = kind;
        p.amount = amount;
        p.phase = Random.value * 10f;
        p.vis = Iso.Child(go.transform, "Sprite").transform;
        Iso.AddSprite(p.vis.gameObject, kind == PickupKind.Gold ? SpriteFactory.Coin : SpriteFactory.Potion, Color.white);
        var shadow = Iso.Child(go.transform, "Shadow");
        shadow.transform.localScale = Vector3.one * 0.4f;
        Iso.AddSprite(shadow, SpriteFactory.Shadow, Color.white, Iso.GroundDecalOrder);

        var col = go.AddComponent<CircleCollider2D>();
        col.isTrigger = true;
        col.radius = 0.2f;
    }

    void Update()
    {
        vis.localPosition = new Vector3(0, 0.03f + Mathf.Abs(Mathf.Sin(Time.time * 3f + phase)) * 0.06f);
        var player = Player.Instance;
        if (player && !player.Health.IsDead && Iso.Distance(transform.position, player.transform.position) < 1.6f)
            transform.position = Vector2.MoveTowards(transform.position, player.transform.position, 4f * Time.deltaTime);
    }

    void OnTriggerEnter2D(Collider2D other)
    {
        var player = other.GetComponent<Player>();
        if (!player) return;
        player.Collect(kind, amount);
        Destroy(gameObject);
    }
}
