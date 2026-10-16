using UnityEditor;

// Import settings for everything under Assets/Resources/Art: crisp, uncompressed pixel art,
// never resized. Runs automatically whenever you add or replace a PNG there.
public class ArtImporter : AssetPostprocessor
{
    void OnPreprocessTexture()
    {
        if (!assetPath.Replace('\\', '/').Contains("/Resources/Art/")) return;
        var ti = (TextureImporter)assetImporter;
        ti.textureType = TextureImporterType.Sprite;
        ti.spriteImportMode = SpriteImportMode.Single;
        ti.spritePixelsPerUnit = 64;
        ti.filterMode = UnityEngine.FilterMode.Point;
        ti.textureCompression = TextureImporterCompression.Uncompressed;
        ti.mipmapEnabled = false;
        ti.alphaIsTransparency = true;
        ti.npotScale = TextureImporterNPOTScale.None;
        ti.maxTextureSize = 8192;
        ti.wrapMode = UnityEngine.TextureWrapMode.Clamp;
    }
}
