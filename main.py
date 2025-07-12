import tkinter as tk
import ctypes
import threading
import keyboard
import hashlib
import time
import os
import pystray
from PIL import Image
import sys

from overlay import Overlay
from region_selector import select_region
from translate import get_text_from_chat, translate_text_google
from log_utils import log_action, log_error, get_last_error

SCAN_INTERVALS = [1, 2, 4, 6, 10]
scan_interval_idx = 1
current_font_size = 12
enabled = True

ICON_FILE = os.path.join(os.path.dirname(sys.argv[0]), "l2t.ico")

HELP_TEXT = """
# L2T Overlay Chat Translator — Help

- Instantly translates your Lineage 2 chat (Russian to English) and overlays it on top of your chat window.
- Overlay is click-through unless you hold Ctrl+Alt, then you can drag it.
- Toggle, font, scan speed, logs, help, etc. from tray menu.

## Shortcuts

| Shortcut             | Action                                           |
|----------------------|-------------------------------------------------|
| Ctrl + Alt + T       | Toggle translation & overlay on/off             |
| Ctrl + Alt + R       | Reselect chat region                            |
| Ctrl + Alt + H       | Show this help/instructions window              |
| (Tray menu only)     | Snap overlay back to chat region                |
| Ctrl + Alt + Drag    | Move overlay window (while keys held)           |

For more, see the README on GitHub.
"""

def main():
    global enabled, scan_interval_idx, current_font_size

    ctypes.windll.user32.SetProcessDPIAware()

    main_root = tk.Tk()
    main_root.withdraw()

    log_action("App started. Beginning region selection...")
    capture_region = select_region(main_root)
    log_action(f"Region selection returned: {capture_region}")

    if not capture_region:
        log_action("No region selected. Exiting.")
        return

    overlay = Overlay(main_root, lambda: capture_region, font_size=current_font_size)
    last_hash = None

    def monitor_chat():
        nonlocal last_hash
        while True:
            try:
                if enabled:
                    text = get_text_from_chat(capture_region, overlay).strip()
                    log_action(f"OCR raw result: '{text}'")
                    if text:
                        text_hash = hashlib.md5(text.encode()).hexdigest()
                        if text_hash != last_hash:
                            last_hash = text_hash
                            translated = translate_text_google(text)
                            log_action(f"Translated text: '{translated}'")
                            if translated:
                                main_root.after(0, overlay.show, translated)
                                log_action("Translated and displayed chat text")
                else:
                    main_root.after(0, overlay.hide)
            except Exception as e:
                log_error(f"Error in monitor_chat: {e}")
            time.sleep(SCAN_INTERVALS[scan_interval_idx])

    def start_monitor():
        threading.Thread(target=monitor_chat, daemon=True).start()
        log_action("Started chat monitor thread")

    def listen_for_hotkeys():
        ctrlalt_prev = False
        while True:
            time.sleep(0.03)
            ctrl = keyboard.is_pressed("ctrl")
            alt = keyboard.is_pressed("alt")
            ctrlalt = ctrl and alt
            if ctrlalt != ctrlalt_prev:
                ctrlalt_prev = ctrlalt
                main_root.after(0, overlay.set_move_mode, ctrlalt)
            if keyboard.is_pressed("ctrl+alt+t"):
                def toggle_en():
                    global enabled
                    enabled = not enabled
                    log_action(f"Toggled all: {'ON' if enabled else 'OFF'} (hotkey)")
                    if not enabled:
                        overlay.hide()
                main_root.after(0, toggle_en)
                time.sleep(0.3)
            if keyboard.is_pressed("ctrl+alt+r"):
                log_action("Region reselect triggered (hotkey)")
                main_root.after(0, do_reselect_region)
                time.sleep(0.3)
            if keyboard.is_pressed("ctrl+alt+h"):
                main_root.after(0, show_help_window)
                time.sleep(0.3)

    def start_hotkey_listener():
        threading.Thread(target=listen_for_hotkeys, daemon=True).start()
        log_action("Started hotkey listener thread")

    def show_help_window():
        help_win = tk.Toplevel(main_root)
        help_win.title("L2T Overlay Help / Instructions")
        help_win.geometry("680x540+480+180")
        help_win.configure(bg="#222")
        text = tk.Text(help_win, font=("Arial", 13), bg="#222", fg="white", wrap="word")
        text.insert("1.0", HELP_TEXT.strip())
        text.config(state="disabled")
        text.pack(padx=16, pady=16, fill="both", expand=True)
        tk.Button(help_win, text="Close", font=("Arial", 12), command=help_win.destroy).pack(pady=8)
        help_win.lift()

    def do_reselect_region(*args):
        nonlocal capture_region
        log_action("Reselect region initiated")
        overlay.hide()
        region = select_region(main_root)
        if region:
            capture_region = region
            overlay.snap_back()
            log_action("Region reselected by user.")

    def snap_overlay_back(icon=None, item=None):
        main_root.after(0, overlay.snap_back)

    def toggle_enabled(icon, item):
        def inner():
            global enabled
            enabled = not enabled
            log_action(f"Toggled all: {'ON' if enabled else 'OFF'} (tray)")
            if not enabled:
                overlay.hide()
        main_root.after(0, inner)

    def set_font_size(size):
        def handler(icon, item):
            def inner():
                global current_font_size
                current_font_size = size
                overlay.set_font_size(size)
                log_action(f"Font size changed to {size}")
            main_root.after(0, inner)
        return handler

    def set_scan_interval(idx):
        def handler(icon, item):
            global scan_interval_idx
            scan_interval_idx = idx
            log_action(f"Scan interval set to {SCAN_INTERVALS[idx]}s")
        return handler

    def view_logs(icon, item):
        log_action("Opened logs via tray")
        log_file = os.path.join(os.path.dirname(sys.argv[0]), "logs.txt")
        try:
            os.startfile(log_file)
        except Exception as e:
            log_error(f"Could not open logs: {e}")

    def show_last_error(icon, item):
        log_action("Show last error tray item selected")
        try:
            win = tk.Toplevel(main_root)
            win.title("Last Error")
            win.geometry("600x150+400+200")
            tk.Label(win, text=get_last_error() or "No errors logged.", font=("Arial", 10), justify="left", wraplength=580).pack(padx=10, pady=10)
            tk.Button(win, text="OK", command=win.destroy).pack(pady=10)
        except Exception as e:
            log_error(f"Error opening error popup: {e}")

    def test_overlay(icon, item):
        main_root.after(0, overlay.show, "Test overlay\nThis is a sample translation box.")

    def show_help(icon, item):
        main_root.after(0, show_help_window)

    def quit_app(icon, item):
        log_action("Exiting app via tray")
        icon.stop()
        os._exit(0)

    def setup_tray():
        from PIL import Image as PILImage
        font_menu = pystray.Menu(
            pystray.MenuItem("Small (9)", set_font_size(9)),
            pystray.MenuItem("Medium (12)", set_font_size(12)),
            pystray.MenuItem("Large (16)", set_font_size(16))
        )
        overlay_menu = pystray.Menu(
            pystray.MenuItem("Toggle On/Off (Ctrl+Alt+T)", toggle_enabled),
            pystray.MenuItem("Snap Overlay Back", snap_overlay_back),
            pystray.MenuItem("Font Size", font_menu),
        )
        scan_menu = pystray.Menu(
            pystray.MenuItem("1s (Fast)", set_scan_interval(0)),
            pystray.MenuItem("2s (Default)", set_scan_interval(1)),
            pystray.MenuItem("4s", set_scan_interval(2)),
            pystray.MenuItem("6s", set_scan_interval(3)),
            pystray.MenuItem("10s (Slow)", set_scan_interval(4))
        )
        diagnostics_menu = pystray.Menu(
            pystray.MenuItem("View Logs", view_logs),
            pystray.MenuItem("Show Last Error", show_last_error),
            pystray.MenuItem("Test Overlay", test_overlay),
        )

        def tray_thread():
            try:
                icon = pystray.Icon(
                    "ChatTranslator",
                    PILImage.open(ICON_FILE),
                    "L2 Chat Translator",
                    menu=pystray.Menu(
                        pystray.MenuItem("Overlay", overlay_menu),
                        pystray.MenuItem("Reselect Region (Ctrl+Alt+R)", lambda icon, item: main_root.after(0, do_reselect_region)),
                        pystray.MenuItem("Scan", scan_menu),
                        pystray.MenuItem("Diagnostics", diagnostics_menu),
                        pystray.MenuItem("Help / Instructions (Ctrl+Alt+H)", show_help),
                        pystray.MenuItem("Exit", quit_app)
                    )
                )
                icon.run_detached()
                log_action("System tray started with run_detached()")
            except Exception as e:
                log_error(str(e))

        threading.Thread(target=tray_thread, daemon=True).start()
        log_action("System tray setup complete (thread started)")

    start_monitor()
    start_hotkey_listener()
    setup_tray()
    log_action("Entering main Tk loop")
    main_root.mainloop()

if __name__ == "__main__":
    main()
