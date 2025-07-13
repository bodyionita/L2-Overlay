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

- Head to [Releases](https://github.com/bodyionita/L2-Overlay/releases) and grab the latest `L2T_Overlay_v0.1.zip`.
- Unzip anywhere.
- Run `L2T_Overlay.exe`.

**No installation, no admin rights needed.**

---

### 2. **Or build from source (for power users!)**

1. **Install Python 3.9+**  
   [Download Python](https://www.python.org/downloads/)

2. **Install dependencies:**  
   Open a terminal in the project folder:
```
pip install -r requirements.txt
```

3. **Install Tesseract OCR**  
- Download and install: [Tesseract Windows installer](https://tesseract-ocr.github.io/tessdoc/Installation.html)
- Make sure to update the path in `main.py` if you used a custom install location.

4. **Run it:**  
```
python main.py
```

5. **(Optional) Build .exe:**  
```
pip install pyinstaller
pyinstaller --onefile --icon l2t.ico main.py
```


---


## 📖 Features & Instructions

### 🛠️ **What does L2T Overlay Chat Translator do?**

- Instantly **translates your Lineage 2 chat** (from Russian to English by default) using Google Translate, and overlays the translation over your game, in real time.
- **Non-intrusive:** Overlay is always click-through (never blocks your mouse/game).
- **Super easy to use:** Just drag to select your chat window once and you're set!
- **All settings available from the tray icon**—adjust font, scan speed, logs, or snap overlay back instantly.
- **Movable overlay:** Hold `Ctrl+Alt` and drag the overlay wherever you want.
- **Open-source and privacy-first:** You see everything, no hidden code, no tracking, only Google Translate used for text translation.
- Visual region border: A fine gold rectangle can be displayed around your selected chat area at all times, helping you remember exactly what will be translated. (Enable or disable at any time from the menu.)
---

### Overlay Region Border

The **Show Region Border** feature draws a fine gold rectangle around the region you selected for translation. This is an independent floating window, always on top and click-through, so it never blocks your game or overlay.

- **Toggle ON/OFF** at any time from the tray or overlay menu ("Show Region Border").
- **The border does not affect translation or overlay position**; it's purely for reference and peace of mind.
- If you change the region, the border instantly updates to match.

---

### 🚦 **Quick Start**

1. **Run the app.**
2. **Select your in-game chat window:**  
- The screen dims and shows instructions.
- **Drag** to select your chat area.
- Release mouse to confirm (ESC to cancel).
3. **Play:**  
- The overlay will appear on top of your chat and update with translations automatically.

---

### ⌨️ **Shortcuts**

---
### ⚠️ Game Hotkey Limitation

**Note:** Hotkeys (Ctrl+Alt+...) do **not** work while the Lineage 2 window is focused, due to the game capturing input.
Use the tray icon, or the header ☰ menu on the overlay, for all controls and settings, including toggling the region border.


---


### 📝 **Tray Menu Features**

- **Overlay**
- Toggle On/Off (same as Ctrl+Alt+T)
- Snap Overlay Back
- Font Size (Small, Medium, Large)
- **Reselect Region** (same as Ctrl+Alt+R)
- **Scan** (change scan interval: 1s, 2s, 4s, 6s, 10s)
- **Diagnostics**
- View Logs (opens `logs.txt`)
- Show Last Error
- Test Overlay
- **Help / Instructions** (same as Ctrl+Alt+H)
- **Exit**

---

### 🔧 **Installation & Setup**

1. **Python users:** See [Installation](#installation) above (Python, Tesseract, pip install requirements).
2. **Everyone else:** Just download the `.exe` release, run, and play!

---

### ❓ **Troubleshooting**

- **Overlay doesn’t appear:** Try running as admin, or check if you have multi-monitor weirdness.
- **No translation:** Ensure Tesseract is installed and path in `main.py` matches.  
- **Overlay stuck or can’t move:** Hold `Ctrl+Alt` and drag, or snap back via tray.
- **Anything else:** Open logs (`logs.txt`), check error in tray, or contact me!
- If the gold border does not appear, try toggling "Show Region Border" off and on in the menu.
- If something is wrong or the overlay is misaligned, use "Reselect Region" or "Snap Overlay Back".
---

### 🔒 **Privacy & Security**

- **100% Open Source**: All code is public, read it yourself!
- **No background uploads, no ads, no tracking.**
- **The only outgoing connection is to Google Translate’s API, to translate your chat.**
- **You can always build from source and verify.**

---

### ⚠️ **Current Limitations**

- Only **Russian-to-English** for now (but can be changed in code easily!)
- Designed/tested on Windows and with LU4, may have quirks elsewhere.
- Built fast—feedback, suggestions, and pull requests are very welcome!

---

### 👤 **Contact**

- **In-game (LU4):** Character: `xTitan`
- **Discord:** `.bogdani`
- **Issues/Suggestions:** [GitHub Issues](https://github.com/bodyionita/L2-Overlay/issues)

---

## Screenshots

![overlay demo](docs/overlay_demo.gif)

---

## Credits

- Built with ❤️ for the LU4 community by `.bogdani`
- Uses [pytesseract](https://github.com/madmaze/pytesseract), [googletrans](https://github.com/ssut/py-googletrans), [pystray](https://github.com/moses-palmer/pystray), [Pillow](https://python-pillow.org/), [tkinter](https://docs.python.org/3/library/tkinter.html)

---
## ☕ Support / Donations

If you found this tool helpful, consider supporting me on [Buy Me a Coffee](https://coff.ee/bodyionita)!

*Every little bit helps me spend more time on helpful indie projects for the L2 and gaming community. Thank you!*
