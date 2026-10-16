# ActionRPG

Isometric 2D pixel-art action RPG for Windows PC (Steam target), built with **Unity 6000.6.6f1** (Unity 6).
You play Aldric, a human warrior, across three regions (Greenhollow forest, Sunscar Wastes desert,
Frostpeak Pass snow). There are real-time sword combat, NPCs with branching conversations, and quests.

## Getting started (Windows or macOS)

1. Install **Unity Hub**, then Unity **6000.6.6f1**. On a Windows PC the Windows build support is
   included; on a Mac, add the module **Windows Build Support (Mono)**.
2. Clone this repo, then in Unity Hub choose **Add > Add project from disk** and pick this folder.
   The first open takes a few minutes while Unity rebuilds its `Library/` cache (not stored in git).
3. Open `Assets/Scenes/Main.unity` and press **Play**.

Controls: **WASD** move · **LMB / J** attack · **Space** roll · **E** talk · **Q** potion · **Esc** pause

## Building the game

Menu **Tools > Build Windows (Steam)** writes `Builds/Windows/ActionRPG.exe` (64-bit, Mono).
From a terminal:

```
<Unity executable> -batchmode -quit -projectPath . -executeMethod BuildScript.BuildWindows -logFile build.log
```

## Where things live

| What | Where |
|---|---|
| Region maps (text grids + legend) | `Assets/Resources/Regions/*.txt`, format explained at the top of each file |
| Conversations | `Assets/Resources/Dialogue/*.txt`, syntax in `Assets/Scripts/Dialogue/DialogueScript.cs` |
| NPC list | `Assets/Resources/Data/npcs.txt` |
| Enemy stats | `Assets/Resources/Data/enemies.txt` |
| Art (sprites, tiles, props, portraits) | `Assets/Resources/Art/`, layout rules in **`ART_SPEC.md`** |
| Game code | `Assets/Scripts/` (Actors, Art, Combat, Core, Data, Dialogue, UI, World) |
| Build script / art import settings | `Assets/Editor/` |
| Placeholder art + map generator | `Tools/placeholder_art/` (optional, needs Python 3) |

The world is built from the text files when you press Play, so the Scene view stays empty in
edit mode. That's expected.

### Writing dialogue (quick reference)

```
# start                         node; conversations begin at "start"
elder: Hello there.             line spoken by an NPC id (or "you" for the player)
[!met_elder] elder: New face!   any line can have a condition in [ ]
~ set met_elder                 actions: set / add / gold / potion / xp / heal
* Ask about wolves -> wolves    player choice
-> end                          jump to a node, or end the conversation
```

Kill counters are automatic: killing a `wolf` adds 1 to `killed_wolf`. Use `{gold}` and similar to show values.

### Regenerating placeholder art (optional)

**Warning:** this overwrites every file in `Assets/Resources/Art/` and every region map.

```
python -m venv Tools/.venv
# Windows:  Tools\.venv\Scripts\pip install numpy pillow
# macOS:    Tools/.venv/bin/pip install numpy pillow
<venv python> Tools/placeholder_art/generate.py      # art
<venv python> Tools/placeholder_art/maps.py          # region maps
```

## Not done yet

Enemy pathfinding around obstacles, save games, quest log, audio, final UI (the HUD uses Unity's
basic built-in GUI), and Steamworks integration.


## How Tos
The Windows build works. Now I'll make the project its own git repository and create the first commit:

  Ran 3 shell commands

The Windows build works and the project is now its own git repository with a first commit. It isn't pushed anywhere yet, because the repo you're connected to is the wrong one.

Don't push the game to that repo. The "github repo" you mean is set up on your whole Documents folder, not on the game:
•⁠  ⁠It points to github.com/IvanReizgas/docs on GitHub, which appears to be someone else's account.
•⁠  ⁠Its only commit, already pushed there, contains play_keystore and upload_certificate.pem. Those look like Android app signing keys. If that repo is public, or not yours, treat the keys as exposed and check with whoever owns them.

How to push the game:
1.⁠ ⁠On github.com, create a new empty repository under your account, e.g. ActionRPG. Leave "Add README" and ".gitignore" unticked. Private is the sensible default for a game you'll sell.
2.⁠ ⁠Send me the repo URL and I'll connect and push, or run it yourself:
cd ~/Documents/games/ActionRPG
git remote add origin https://github.com/<you>/ActionRPG.git
git push -u origin main
   GitHub will ask you to log in. For HTTPS it needs a personal access token, not your password. GitHub Desktop is the easiest option if you'd rather not deal with tokens.

Later, on a PC: install Unity Hub and Unity 6000.6.6f1, run git clone <url>, then in Unity Hub use Add project from disk and press Play. T

Why it doesn't depend on macOS:
•⁠  ⁠Only the project's own files are in git: Assets, Packages and ProjectSettings. Unity's machine-specific cache (Library/), builds, logs and editor files are excluded and get rebuilt automatically on each computer.
•⁠  ⁠A .gitattributes file keeps Windows and Mac line endings from conflicting, and marks images and sounds as binary.
•⁠  ⁠Unity saves its scene and settings files as text, which merge cleanly.
•⁠  ⁠The code has no Mac-only parts. The optional Python art generator also runs on Windows; the README has the Windows commands.

Build: Builds/Windows/ActionRPG.exe built successfully (102 MB). Copy the whole Builds/Windows folder to a Windows PC to run it; the .exe 't run it, since .exe files don't run on macOS.

Once you're making real art, consider Git LFS for large image and sound files. At 2.7 MB of assets today it isn't needed.

✻ Brewed for 1m 50s · done 12:24

※ recap: We're building your isometric pixel-art RPG for a Windows Steam release; the Windows build works and the project has its own git rext: create an empty private GitHub repo and send me its URL so I can push. (disable recaps in /config)

❯ i added UnityActionGame in git

  Ran 1 shell command

I can't connect it yet: I don't know which GitHub account the repo is under. The game folder has no remote set, and the only remote on thi IvanReizgas/docs one, which I'm leaving alone.

Can you paste the full URL of the new repo? You can copy it from the green Code button on its GitHub page; it looks like:

https://github.com/<your-username>/UnityActionGame.git

Once I have it, I'll connect the project and push the first commit. If GitHub asks for a login during the push, you'll need a personal acc password; I'll walk you through that if it comes up.

✻ Brewed for 20s · done 12:28

❯ https://github.com/IvanReizgas/UnityActionGame

  Ran 1 shell command

The repo is reachable and empty, so nothing gets overwritten. Pushing:

  Ran 1 shell command

GitHub returned HTTP 400 during the upload. That usually means git's upload buffer is too small for a first push of this size. I'll raise retry:

  Pushed to main

The project is on GitHub at https://github.com/IvanReizgas/UnityActionGame, on the main branch. Your local copy is linked to it and fully

The first push failed with an HTTP 400 error. I raised git's upload buffer for this repo only (a common fix for a large first push), and tough.

Day-to-day on either machine:
git pull                         # start of a session: get the latest
git add -A
git commit -m "what you changed"
git push                         # end of a session: upload

On the PC: git clone https://github.com/IvanReizgas/UnityActionGame.git, add the folder in Unity Hub with Unity 6000.6.6f1, open Assets/ScPlay. The README in the repo has the full steps.

The docs repo on the same account still contains the pushed play_keystore and upload_certificate.pem. If that repo is public, make it priv

There are two ways, depending on whether you're on your Mac or a Windows PC.

On your Mac, inside the Unity editor:
1.⁠ ⁠Open Unity Hub. If ActionRPG isn't listed, choose Add → Add project from disk and select ~/Documents/games/ActionRPG.
2.⁠ ⁠Open the project; the first time takes a moment.
3.⁠ ⁠In the Project panel at the bottom, double-click Assets/Scenes/Main.unity.
4.⁠ ⁠Press the ▶ Play button at the top centre. The game runs in the Game tab.
5.⁠ ⁠Click inside the Game tab so it receives your keyboard input. Press ▶ again to stop.

To get a larger view, click Maximize On Play in the Game tab's toolbar before pressing Play.

The Scene tab stays empty until you press Play, because the world is built from the map text files when the game starts. That's expected.

On a Windows PC:
•⁠  ⁠From the build: copy the whole Builds/Windows folder from your Mac to the PC, not just the .exe, and double-click ActionRPG.exe. This build is excluded from git, so it isn't on GitHub. Bring it over another way, such as a USB stick or a cloud drive. You can always make a fresh one in Unity with Tools → Build Windows (Steam).
•⁠  ⁠From GitHub: clone the repo, open it in Unity Hub, then press Play as on the Mac.

Controls: WASD to move, left-click or J to attack, Space to roll, E to talk to someone nearby, Q to drink a potion, Esc to pause.

Worth trying:
•⁠  ⁠Village: you start in Greenhollow. Talk to Elder Maren (purple robe) to get the wolf quest, to Tobin (green tunic) to buy potions, and to Captain Brann (guard) for the bandit quest.
•⁠  ⁠Wolves: they're in the forest clearings, up-left and up-right of the village. After killing 3, go back to Maren for your reward.
•⁠  ⁠Desert: follow the path to the right edge of the map. Zahra at the oasis has a quest.
•⁠  ⁠Snow: follow the path to the top edge. Eskil is at the hunter camp.

Your walking GIFs are now the warrior's walk animation, in all 8 directions with 8 frames each. In the preview the feet sit on the same line in every frame, so he won't jitter or float while walking. I haven't seen it in the game yet because the Unity Editor is open; press Play to try it.

•⁠  ⁠Speed: your GIFs run at 200 ms per frame (5 frames per second). That's slow for in-game walking and would make the feet look like they're sliding, so I set the walk to 10 fps, which matches his movement speed better. To change it, edit "fps" under walk in Assets/Resources/Art/Characters/warrior/character.json. 8 is calmer, 12 is brisker.
•⁠  ⁠Idle and attack are still generated from your single rotation pose: a breathing idle and a forward lunge. If you make GIFs for those too, I'll add them the same way.

The import script now accepts GIFs, one per direction. The {dir} placeholder stands for the 8 direction names your files use. For later imports, or for attack GIFs:
Tools/.venv/bin/python Tools/import_character.py "<rotations.zip>" warrior --portrait warrior \
  --anim walk="~/Downloads/feet_longer_realist_v3_walking_{dir}.gif" \
  --anim attack="~/Downloads/<name>attack{dir}.gif"

Your GIFs are copied to ArtSource/warrior/walk/, next to the original rotations, so they won't be lost if you clear out Downloads. None of this is committed yet.
