using System.IO;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;

// Builds the Windows PC version (the Steam target).
//   In Unity:      menu Tools > Build Windows (Steam)
//   Command line:  Unity -batchmode -quit -projectPath . -executeMethod BuildScript.BuildWindows
// Requires the "Windows Build Support (Mono)" module in Unity Hub.
public static class BuildScript
{
    const string ScenePath = "Assets/Scenes/Main.unity";
    const string WindowsOutput = "Builds/Windows/ActionRPG.exe";

    [MenuItem("Tools/Setup Main Scene")]
    public static void EnsureProjectSetup()
    {
        if (!File.Exists(ScenePath))
        {
            Directory.CreateDirectory("Assets/Scenes");
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var cam = new GameObject("Main Camera").AddComponent<Camera>();
            cam.tag = "MainCamera";
            new GameObject("GameManager").AddComponent<GameManager>();
            EditorSceneManager.SaveScene(scene, ScenePath);
        }
        EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(ScenePath, true) };

        PlayerSettings.productName = "ActionRPG";
        PlayerSettings.companyName = "sebastiankrueger";
        // Typical PC/Steam defaults: borderless fullscreen at the desktop resolution, resizable when windowed.
        PlayerSettings.fullScreenMode = FullScreenMode.FullScreenWindow;
        PlayerSettings.defaultScreenWidth = 1920;
        PlayerSettings.defaultScreenHeight = 1080;
        PlayerSettings.resizableWindow = true;
        PlayerSettings.runInBackground = false;
        PlayerSettings.SetScriptingBackend(NamedBuildTarget.Standalone, ScriptingImplementation.Mono2x);
        AssetDatabase.SaveAssets();
    }

    [MenuItem("Tools/Build Windows (Steam)")]
    public static void BuildWindows()
    {
        if (!BuildPipeline.IsBuildTargetSupported(BuildTargetGroup.Standalone, BuildTarget.StandaloneWindows64))
        {
            Debug.LogError("Windows Build Support is not installed. Unity Hub > Installs > this version > Add modules > Windows Build Support (Mono).");
            if (Application.isBatchMode) EditorApplication.Exit(1);
            return;
        }
        if (EditorUserBuildSettings.activeBuildTarget != BuildTarget.StandaloneWindows64)
            EditorUserBuildSettings.SwitchActiveBuildTarget(BuildTargetGroup.Standalone, BuildTarget.StandaloneWindows64);

        EnsureProjectSetup();
        var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions
        {
            scenes = new[] { ScenePath },
            locationPathName = WindowsOutput,
            target = BuildTarget.StandaloneWindows64,
        });
        Debug.Log($"Build result: {report.summary.result}, {report.summary.totalErrors} errors, {report.summary.totalSize / (1024 * 1024)} MB -> {WindowsOutput}");
        if (report.summary.result != BuildResult.Succeeded && Application.isBatchMode) EditorApplication.Exit(1);
    }
}
