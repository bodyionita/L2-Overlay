# L2T Overlay Chat Translator

![screenshot](docs/screenshot.png)

## What is this?

**L2T Overlay Chat Translator** is a free and open-source tool for Lineage 2 Masterwork (LU4) players.  
It lets you select your in-game chat window, then overlays instant, live Google translation right on your screen—without modifying the game.

- **Click-through overlay** (won't block your game!).
- **Easy region select** (drag and drop on startup or with a hotkey).
- **Overlay is movable**—just hold `Ctrl+Alt` and drag.
- **Snaps back** to your chat region with one tray menu click.
- **System tray** for all settings: font, scan speed, logs, help, more!
- **Privacy-first:** Your screen is never sent anywhere except to Google Translate, for translation only.

---

## Installation

### 1. **Download the release**

- Head to [Releases](https://github.com/YOURNAME/l2t-overlay-chat-translator/releases) and grab the latest `L2T_Overlay_v0.1.zip`.
- Unzip anywhere.
- Run `L2T_Overlay.exe`.

**No installation, no admin rights needed.**

---

### 2. **Or build from source (for power users!)**

1. **Install Python 3.9+**  
   [Download Python](https://www.python.org/downloads/)

2. **Install dependencies:**  
   Open a terminal in the project folder:
```pip install -r requirements.txt```

3. **Install Tesseract OCR**  
- Download and install: [Tesseract Windows installer](https://tesseract-ocr.github.io/tessdoc/Installation.html)
- Make sure to update the path in `main.py` if you used a custom install location.

4. **Run it:**  
```python main.py```

5. **(Optional) Build .exe:**  
```pip install pyinstaller
pyinstaller --onefile --icon l2t.ico main.py```


---

## How to Use

1. **On first run, select your chat region.**
2. **Overlay appears over chat and translates automatically.**
3. **System tray menu lets you toggle, adjust, or open logs.**
4. **Drag overlay with `Ctrl+Alt` + mouse.**
5. **Snap overlay back via tray menu.**
6. **Reselect region with `Ctrl+Alt+R`.**
7. **Show help any time with `Ctrl+Alt+H` or tray menu.**

---

## Privacy and Trust

- **Open Source:** All code is on GitHub—inspect, fork, or contribute!
- **No spyware, no hidden code, no networking except for Google Translate.**
- **No data is ever stored or sent anywhere but Google (for translation only).**
- **You can build it yourself!**

### **Troubleshooting**

- If translation doesn’t work, check logs in `logs.txt` (open via tray menu).
- Overlay won’t move? Hold `Ctrl+Alt` and drag.
- OCR weird? Try selecting a tighter region or changing font size in tray.
- Crashes? Make sure Tesseract is installed and working.

---

## Current Limitations

- **Only supports Russian-to-English** (more languages in the future—pull requests welcome!)
- **Performance:** Built fast, may stutter on very slow PCs, especially when selecting region. Suggestions welcome!
- Overlay drag is only available when holding `Ctrl+Alt`.
- Game resolution/DPI weirdness may cause bugs.

---

## Contact

**In-game (LU4):**  
Character: `xTitan`

**Discord:**  
`.bogdani`

**Want to contribute or suggest improvements?**  
- Open an [issue](https://github.com/YOURNAME/l2t-overlay-chat-translator/issues) or [pull request](https://github.com/YOURNAME/l2t-overlay-chat-translator/pulls)!

---

## Screenshots

![overlay demo](docs/overlay_demo.gif)

---

## Credits

- Built with ❤️ for the LU4 community by `.bogdani`
- Uses [pytesseract](https://github.com/madmaze/pytesseract), [googletrans](https://github.com/ssut/py-googletrans), [pystray](https://github.com/moses-palmer/pystray), [Pillow](https://python-pillow.org/), [tkinter](https://docs.python.org/3/library/tkinter.html)
