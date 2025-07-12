import pytesseract
from PIL import ImageGrab, Image, ImageTk, ImageDraw
from googletrans import Translator
import threading
import time
import hashlib
import win32gui
import win32con
import tkinter as tk
import pystray
import os
import sys
import ctypes
import keyboard
import traceback
from datetime import datetime

# === LOGGING ===

last_error = ""

def log_action(message):
    log_error("[ACTION] " + message)

def log_error(message):
    global last_error
    last_error = message
    ts = f"[{datetime.now()}] "
    msg = ts + message.strip()
    print("Logging:", msg)
    try:
        log_file = os.path.join(os.path.dirname(sys.argv[0]), "logs.txt")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        return
    error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    log_error(error_msg)

sys.excepthook = handle_exception

# === CONFIG ===

pytesseract.pytesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
SCAN_INTERVALS = [1, 2, 4, 6, 10]
scan_interval_idx = 1  # default to 2s

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller extracts files to _MEIPASS
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

ICON_FILE = resource_path("l2t.ico")

HELP_TEXT = """
L2 Chat Overlay Translator – Help

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURES
• Translates your Lineage 2 chat (Russian → English) and overlays result in-place.
• Overlay is click-through by default. Hold Ctrl+Alt to drag/move the overlay window.
• Tray icon and global hotkeys control everything. All logs/errors saved to logs.txt.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SHORTCUTS
• Ctrl+Alt+T   — Enable/Disable overlay + translation
• Ctrl+Alt+R   — Reselect chat region (output snaps back to region)
• Ctrl+Alt+H   — Show this help window
• Ctrl+Alt+Drag — Move overlay with the mouse while holding keys

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TRAY MENU
• Overlay → Toggle, Snap Overlay Back (realign overlay to region), Font Size
• Scan → Scan Interval (how often chat is translated)
• Diagnostics → View logs, Show last error, Test overlay
• Help, Exit

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
USAGE NOTES
• On startup, select your in-game chat region by click+drag. (ESC cancels.)
• Overlay never captures itself (temporarily hidden during OCR).
• Dragging the overlay does NOT affect the region being translated.
• Overlay is click-through except when you hold Ctrl+Alt.
• Use "Snap Overlay Back" in tray or reselect region (Ctrl+Alt+R) to realign overlay.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TROUBLESHOOTING / LIMITATIONS
• Only translates Russian → English.
• OCR accuracy may vary with chat fonts/backgrounds.
• If translation or OCR ever stalls (more than 3 seconds), it's auto-cancelled and retried.
• Google Translate may rate-limit on rapid use.
• Logs and errors: See logs.txt (Diagnostics in tray menu).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONTACT
• Discord: .bogdani
• GitHub: https://github.com/bodyionita/L2-Overlay
"""

# === STATE ===

translator = Translator()
last_hash = None
enabled = True  # single flag for overlay+translation
capture_region = None
overlay_window = None
overlay_label = None
overlay_position = None  # (x, y) if user moves overlay, None=stick to region
current_font_size = 12
monitor_thread = None
hotkey_thread = None
move_mode = False   # True when Ctrl+Alt is held
main_root = tk.Tk()
main_root.withdraw()

selecting_region = False

# === OVERLAY CLICK-THROUGH CONTROL ===

def set_overlay_clickthrough(enable):
    global overlay_window
    if overlay_window and overlay_window.winfo_exists():
        overlay_window.update_idletasks()
        hwnd = win32gui.FindWindow(None, overlay_window.title())
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        if enable:
            style = style | win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT
        else:
            style = (style | win32con.WS_EX_LAYERED) & ~win32con.WS_EX_TRANSPARENT
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, style)

def start_move(event):
    if not move_mode: return
    overlay_window._drag_start_x = event.x
    overlay_window._drag_start_y = event.y

def do_move(event):
    global overlay_position
    if not move_mode: return
    x = overlay_window.winfo_x() + event.x - overlay_window._drag_start_x
    y = overlay_window.winfo_y() + event.y - overlay_window._drag_start_y
    overlay_window.geometry(f"+{x}+{y}")
    overlay_position = (x, y)

def end_move(event):
    global overlay_position
    if not move_mode: return
    x = overlay_window.winfo_x()
    y = overlay_window.winfo_y()
    overlay_position = (x, y)
    log_action(f"Overlay moved to ({x}, {y}) by mouse drag")

def update_overlay_drag_bindings():
    if overlay_window and overlay_window.winfo_exists():
        overlay_label.unbind('<Button-1>')
        overlay_label.unbind('<B1-Motion>')
        overlay_label.unbind('<ButtonRelease-1>')
        overlay_window.unbind('<Button-1>')
        overlay_window.unbind('<B1-Motion>')
        overlay_window.unbind('<ButtonRelease-1>')
        if move_mode:
            overlay_label.bind('<Button-1>', start_move)
            overlay_label.bind('<B1-Motion>', do_move)
            overlay_label.bind('<ButtonRelease-1>', end_move)
            overlay_window.bind('<Button-1>', start_move)
            overlay_window.bind('<B1-Motion>', do_move)
            overlay_window.bind('<ButtonRelease-1>', end_move)
            overlay_label.config(cursor="fleur")
        else:
            overlay_label.config(cursor="")

# === SNAP BACK ===

def snap_overlay_back(icon=None, item=None):
    global overlay_position, capture_region, overlay_window
    if capture_region and overlay_window:
        x1, y1, x2, y2 = capture_region
        overlay_position = None
        width = x2 - x1
        height = y2 - y1
        overlay_window.geometry(f"{width}x{height}+{x1}+{y1}")
        log_action(f"Overlay snapped back to ({x1},{y1})")
    else:
        log_action("Snap back failed: overlay or region missing")

# === TRANSLATION ===

def translate_text_google(text):
    try:
        result = translator.translate(text, src='ru', dest='en')
        return result.text
    except Exception as e:
        log_error(f"Translation error: {e}")
        return f"[Translation Error] {e}"

def get_text_from_chat():
    if not capture_region:
        return ""
    try:
        hide_overlay()
        time.sleep(0.08)
        image = ImageGrab.grab(bbox=capture_region)
        if enabled:
            overlay_window and overlay_window.deiconify()
        return pytesseract.image_to_string(image, lang='rus+eng')
    except Exception as e:
        log_error(f"OCR error: {e}")
        return ""

def _show_translation_tk(text):
    global overlay_window, overlay_label, overlay_position
    try:
        if not enabled:
            log_action("Overlay not shown (disabled)")
            if overlay_window:
                overlay_window.withdraw()
            return

        x1, y1, x2, y2 = capture_region
        width = x2 - x1
        height = y2 - y1

        if overlay_position is not None:
            ox, oy = overlay_position
        else:
            ox, oy = x1, y1

        create_new = (overlay_window is None or not overlay_window.winfo_exists())
        if create_new:
            overlay_window = tk.Toplevel(main_root)
            overlay_window.title("Translation")
            overlay_window.geometry(f"{width}x{height}+{ox}+{oy}")
            overlay_window.wm_attributes("-topmost", True)
            overlay_window.attributes("-alpha", 0.7)
            overlay_window.configure(bg="black")
            overlay_window.overrideredirect(True)

            overlay_label = tk.Label(
                overlay_window,
                text=text,
                font=("Arial", current_font_size),
                bg="black",
                fg="yellow",
                justify="left",
                anchor="nw"
            )
            overlay_label.pack(fill="both", expand=True, padx=5, pady=5)

            set_overlay_clickthrough(True)
            update_overlay_drag_bindings()
            log_action("Created overlay window")
        else:
            overlay_window.geometry(f"{width}x{height}+{ox}+{oy}")

        overlay_label.config(text=text, font=("Arial", current_font_size))
        overlay_window.deiconify()
        overlay_window.lift()
        set_overlay_clickthrough(not move_mode)
        update_overlay_drag_bindings()
        log_action("Updated overlay with new translation")

    except Exception:
        log_error(traceback.format_exc())

def show_translation(text):
    main_root.after(0, _show_translation_tk, text)

def hide_overlay():
    global overlay_window
    if overlay_window:
        overlay_window.withdraw()

def monitor_chat():
    global last_hash
    while True:
        try:
            if enabled and not selecting_region:
                text = get_text_from_chat().strip()
                if text:
                    text_hash = hashlib.md5(text.encode()).hexdigest()
                    if text_hash != last_hash:
                        last_hash = text_hash
                        translated = translate_text_google(text)
                        if translated:
                            show_translation(translated)
                            log_action("Translated and displayed chat text")
            else:
                hide_overlay()
            time.sleep(SCAN_INTERVALS[scan_interval_idx])
        except Exception:
            log_error(traceback.format_exc())

def start_monitoring():
    global monitor_thread
    monitor_thread = threading.Thread(target=monitor_chat, daemon=True)
    monitor_thread.start()
    log_action("Started chat monitor thread")

# === HOTKEY & GLOBAL KEYS LISTENER ===

def show_help_window():
    log_action("Help window opened")
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

def listen_for_hotkeys():
    global enabled, overlay_window, move_mode
    ctrlalt_prev = False
    while True:
        time.sleep(0.03)
        ctrl = keyboard.is_pressed("ctrl")
        alt = keyboard.is_pressed("alt")
        ctrlalt = ctrl and alt
        if ctrlalt != ctrlalt_prev:
            ctrlalt_prev = ctrlalt
            move_mode = ctrlalt
            if overlay_window and overlay_window.winfo_exists():
                if move_mode:
                    set_overlay_clickthrough(False)
                else:
                    set_overlay_clickthrough(True)
                update_overlay_drag_bindings()
        # Process hotkeys for functions (so hotkeys don't interfere with drag detection)
        if keyboard.is_pressed("ctrl+alt+t"):
            enabled = not enabled
            log_action(f"Toggled all: {'ON' if enabled else 'OFF'} (hotkey)")
            if not enabled:
                hide_overlay()
            time.sleep(0.3)
        if keyboard.is_pressed("ctrl+alt+r"):
            log_action("Region reselect triggered (hotkey)")
            main_root.after(0, reselect_region)
            time.sleep(0.3)
        if keyboard.is_pressed("ctrl+alt+h"):
            main_root.after(0, show_help_window)
            time.sleep(0.3)

def start_hotkey_listener():
    global hotkey_thread
    hotkey_thread = threading.Thread(target=listen_for_hotkeys, daemon=True)
    hotkey_thread.start()
    log_action("Started hotkey listener thread")

# === REGION SELECTOR WITH GLASS EFFECT ===

def select_region(allow_cancel=True):
    global selecting_region, capture_region, overlay_position
    selecting_region = True
    region = []
    overlay_position = None  # reset output position to match region

    root = tk.Toplevel(main_root)
    root.attributes("-fullscreen", True)
    root.attributes("-alpha", 1.0)
    root.configure(bg='black')
    root.title("Select Chat Region")

    try:
        screen_image = ImageGrab.grab()
    except Exception as e:
        log_error(f"Could not grab screen for selection: {e}")
        screen_image = Image.new("RGB", (1920, 1080), "black")  # fallback

    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    screen_pil = screen_image.resize((screen_w, screen_h)).convert('RGB')

    canvas = tk.Canvas(root, bg='black', highlightthickness=0)
    canvas.pack(fill=tk.BOTH, expand=True)

    screen_photo_img = ImageTk.PhotoImage(screen_pil)
    canvas.create_image(0, 0, anchor="nw", image=screen_photo_img)
    canvas.screen_photo_img = screen_photo_img

    overlay_img = Image.new("RGBA", (screen_w, screen_h), (0, 0, 0, 128))
    overlay_photo = ImageTk.PhotoImage(overlay_img)
    overlay_id = canvas.create_image(0, 0, anchor="nw", image=overlay_photo)
    canvas.overlay_photo = overlay_photo

    selection_box = None
    start_x = start_y = 0

    instruction_label = tk.Label(
        root,
        text="🖱 Click and drag to select your in-game chat window.\nRelease mouse to confirm. Press ESC to cancel.",
        font=("Arial", 28, "bold"),
        bg="#222",
        fg="white"
    )
    instruction_label.place(relx=0.5, rely=0.5, anchor="center")
    instruction_label.lift()

    def update_overlay(x0, y0, x1, y1):
        overlay = Image.new("RGBA", (screen_w, screen_h), (0, 0, 0, 128))
        draw = ImageDraw.Draw(overlay)
        draw.rectangle([x0, y0, x1, y1], fill=(0, 0, 0, 0))
        photo = ImageTk.PhotoImage(overlay)
        canvas.itemconfig(overlay_id, image=photo)
        canvas.overlay_photo = photo

    def on_click(event):
        nonlocal start_x, start_y, selection_box
        start_x, start_y = event.x, event.y
        if selection_box:
            canvas.delete(selection_box)
            selection_box = None
        selection_box = canvas.create_rectangle(start_x, start_y, start_x, start_y, outline='red', width=3)
        update_overlay(start_x, start_y, start_x, start_y)
        instruction_label.lift()

    def on_drag(event):
        if selection_box:
            canvas.coords(selection_box, start_x, start_y, event.x, event.y)
        update_overlay(min(start_x, event.x), min(start_y, event.y), max(start_x, event.x), max(start_y, event.y))
        instruction_label.lift()

    def on_release(event):
        nonlocal region
        x1, y1 = root.winfo_rootx() + start_x, root.winfo_rooty() + start_y
        x2, y2 = root.winfo_rootx() + event.x, root.winfo_rooty() + event.y
        region = [min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)]
        root.destroy()
        log_action(f"Selected region: {region}")

    def on_escape(event):
        log_error("User canceled region selection.")
        region.clear()
        root.destroy()

    canvas.bind("<Button-1>", on_click)
    canvas.bind("<B1-Motion>", on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)
    if allow_cancel:
        root.bind("<Escape>", on_escape)
    root.grab_set()
    main_root.wait_window(root)

    selecting_region = False
    if region:
        capture_region = tuple(region)
        log_action(f"Region set to {capture_region}")

def reselect_region():
    global capture_region, overlay_window, overlay_position
    log_action("Reselect region initiated (tray/hotkey)")
    capture_region = None
    overlay_position = None
    if overlay_window:
        overlay_window.withdraw()
    select_region()
    log_action("Region reselected by user.")

# === SYSTEM TRAY ===

def toggle_enabled(icon, item):
    global enabled, overlay_window
    enabled = not enabled
    log_action(f"Toggled all: {'ON' if enabled else 'OFF'} (tray)")
    if not enabled:
        hide_overlay()

def set_font_size(size):
    def handler(icon, item):
        global current_font_size, overlay_label
        current_font_size = size
        log_action(f"Font size changed to {size}")
        if overlay_label:
            overlay_label.config(font=("Arial", current_font_size))
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
    global last_error
    log_action("Show last error tray item selected")
    try:
        win = tk.Toplevel(main_root)
        win.title("Last Error")
        win.geometry("600x150+400+200")
        tk.Label(win, text=last_error or "No errors logged.", font=("Arial", 10), justify="left", wraplength=580).pack(padx=10, pady=10)
        tk.Button(win, text="OK", command=win.destroy).pack(pady=10)
    except Exception as e:
        log_error(f"Error opening error popup: {e}")

def test_overlay(icon, item):
    log_action("Test overlay tray item selected")
    show_translation("Test overlay\nThis is a sample translation box.")

def show_help(icon, item):
    main_root.after(0, show_help_window)

def quit_app(icon, item):
    log_action("Exiting app via tray")
    icon.stop()
    os._exit(0)

def setup_tray():
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
            from PIL import Image
            icon = pystray.Icon(
                "ChatTranslator",
                Image.open(ICON_FILE),
                "L2 Chat Translator",
                menu=pystray.Menu(
                    pystray.MenuItem("Overlay", overlay_menu),
                    pystray.MenuItem("Reselect Region (Ctrl+Alt+R)", lambda icon, item: main_root.after(0, reselect_region)),
                    pystray.MenuItem("Scan", scan_menu),
                    pystray.MenuItem("Diagnostics", diagnostics_menu),
                    pystray.MenuItem("Help / Instructions (Ctrl+Alt+H)", show_help),
                    pystray.MenuItem("Exit", quit_app)
                )
            )
            icon.run()
        except Exception:
            log_error(traceback.format_exc())

    threading.Thread(target=tray_thread, daemon=True).start()
    log_action("System tray setup complete")

# === MAIN ===

if __name__ == "__main__":
    ctypes.windll.user32.SetProcessDPIAware()
    log_action("App started")
    select_region()

    if capture_region:
        start_monitoring()
        start_hotkey_listener()
        setup_tray()
        main_root.mainloop()
    else:
        log_action("No region selected. Exiting.")
