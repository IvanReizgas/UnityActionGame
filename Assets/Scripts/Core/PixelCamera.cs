using UnityEngine;

// Pixel-perfect follow camera: picks an integer zoom so every art pixel is an exact block of screen pixels.
public class PixelCamera : MonoBehaviour
{
    public static PixelCamera Instance { get; private set; }

    // Roughly how many art pixels tall the view should be; the zoom is rounded to an integer.
    const float TargetHeightPixels = 360f;

    public Transform target;
    public int Zoom { get; private set; } = 2;

    Camera cam;
    Vector3 basePos;
    float shake;
    int lastScreenH;

    void Awake()
    {
        Instance = this;
        cam = GetComponent<Camera>();
        basePos = transform.position;
    }

    public void Shake(float amount) => shake = Mathf.Max(shake, amount);

    public void Snap()
    {
        if (!target) return;
        basePos = Goal();
        transform.position = basePos;
    }

    Vector3 Goal() => new Vector3(target.position.x, target.position.y + 0.35f, -10f);

    void LateUpdate()
    {
        if (Screen.height != lastScreenH)
        {
            lastScreenH = Screen.height;
            Zoom = Mathf.Max(1, Mathf.RoundToInt(Screen.height / TargetHeightPixels));
            cam.orthographicSize = Screen.height / (2f * ArtLibrary.PPU * Zoom);
        }
        if (target)
            basePos = Vector3.Lerp(basePos, Goal(), 1f - Mathf.Exp(-8f * Time.unscaledDeltaTime));
        shake = Mathf.MoveTowards(shake, 0f, Time.unscaledDeltaTime * 0.5f);

        // snap to the screen-pixel grid to avoid shimmering
        float unit = 1f / (ArtLibrary.PPU * Zoom);
        var p = basePos + (Vector3)(Random.insideUnitCircle * shake);
        p.x = Mathf.Round(p.x / unit) * unit;
        p.y = Mathf.Round(p.y / unit) * unit;
        transform.position = p;
    }
}
