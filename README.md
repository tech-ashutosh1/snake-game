Finger Snake Game
=================

Controls
- Show index finger on camera to start (menu)
- Q or ESC: Quit
- P: Pause / Resume
- M: Mute / Unmute audio

Features added
- Pause (P) freezes game updates and shows PAUSED overlay.
- Mute (M) toggles audio (placeholder hook; audio playback should check `self.muted`).
- On-screen hint added to the menu: `Press Q to quit | P to pause | M to mute`.
- High-score persistence: best score saved to `highscore.json` in the project root.

How to run
1. Activate the virtualenv:

```bash
source myEnv/bin/activate
```

2. Install requirements (if not already installed):

```bash
python -m pip install -r requirements.txt
```

3. Run the game:

```bash
python main.py
```

Notes
- On macOS you may need to allow camera access in System Settings > Privacy & Security.
- Mediapipe and related packages are large; installation can take time and disk space.

If you want, I can now:
- Wire audio playback to respect `self.muted` (search for places where sounds are played).
- Show the high score on the menu screen more prominently.
- Add a quick unit test for snake collision logic.
