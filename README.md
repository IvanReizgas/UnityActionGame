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
