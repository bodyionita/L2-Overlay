import pytesseract
from PIL import ImageGrab, Image, ImageTk, ImageDraw, ImageFont
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
import traceback
from datetime import datetime
import concurrent.futures

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
SCAN_INTERVALS = [1, 2, 5, 10, 30]
scan_interval_idx = 3  # default to 5s

HELP_TEXT = """
L2 Chat Overlay Translator – Help

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURES
• Translates your Lineage 2 chat (Russian → English) and overlays result in-place.
• Overlay header is always visible, always clickable (status, ☰ menu).
• Translation region never flickers; only its text changes.
• Font size can be auto-fit or fixed (window grows to fit).
• **New:** A gold border can be displayed around your selected chat region for easy visual reference. Enable/disable in the menu ("Show Region Border").
• Tray menu and overlay ☰ menu control everything. All logs/errors saved to logs.txt.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TRAY & OVERLAY MENU
• Overlay → Toggle, Snap Overlay Back, Font Size, Border, Show Region Border
• Scan → Scan Interval (how often chat is translated)
• Diagnostics → View logs, Show last error, Test overlay
• Help, Exit

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
USAGE NOTES
• On startup, select your in-game chat region by click+drag. (ESC cancels.)
• Overlay never captures itself (temporarily blanks text during OCR).
• A gold border box highlights your selected region. Toggle it ON/OFF from any menu.
• Dragging the overlay region or header does NOT affect the region being translated.
• Overlay is click-through except when you move it.
• Use "Snap Overlay Back" in menu or reselect region to realign overlay.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SHORTCUTS
• Global hotkeys (Ctrl+Alt+...) are unreliable in-game (Lineage 2 often captures them).  
• Always use the tray icon or overlay menu (☰) for control.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TROUBLESHOOTING / LIMITATIONS
• Only translates Russian → English.
• OCR accuracy may vary with chat fonts/backgrounds.
• If translation or OCR ever stalls (more than 3 seconds), it's auto-cancelled and retried.
• Google Translate may rate-limit on rapid use.
• Logs and errors: See logs.txt (Diagnostics in tray/menu).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONTACT
• Discord: .bogdani
• GitHub: https://github.com/bodyionita/L2-Overlay
"""


# === STATE ===

translator = Translator()
last_hash = None
enabled = True  # overlay+translation enabled/disabled
capture_region = None
overlay_window = None
overlay_label = None
overlay_position = None  # (x, y) if user moves overlay, None=stick to region
current_font_size = 12
font_mode = "auto"  # "auto" or "fixed"
monitor_thread = None
move_mode = False   # True when moving overlay
main_root = tk.Tk()
main_root.withdraw()
border_mode = "none"  # "none" or "thin"

# === BORDER BOX STATE ===
region_border_enabled = True
region_border_window = None

# === HEADER WINDOW (MENU + STATUS) ===
header_window = None
status_label = None
menu_btn = None

# === ANIMATION STATE ===
busy_anim_running = False
busy_anim_dots = 0

selecting_region = False

# === TRAY ICON (GENERATED IN MEMORY) ===
def generate_tray_icon():
    size = 64
    img = Image.new('RGBA', (size, size), (112, 0, 36, 255))  # burgundy
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arialbd.ttf", 34)
    except:
        font = ImageFont.load_default()
    text = "L2T"
    tw, th = draw.textbbox((0, 0), text, font=font)[2:]
    draw.text(((size-tw)//2, (size-th)//2), text, font=font, fill=(255,215,0,255))
    return img

# === REGION BORDER BOX ===

def show_region_border():
    global region_border_window, capture_region, region_border_enabled
    if not region_border_enabled or not capture_region:
        hide_region_border()
        return
    if region_border_window and region_border_window.winfo_exists():
        region_border_window.destroy()
    x1, y1, x2, y2 = capture_region
    width = x2 - x1
    height = y2 - y1
    region_border_window = tk.Toplevel(main_root)
    region_border_window.geometry(f"{width}x{height}+{x1}+{y1}")
    region_border_window.overrideredirect(True)
    region_border_window.wm_attributes("-topmost", True)
    region_border_window.attributes("-alpha", 1.0)
    region_border_window.wm_attributes("-transparentcolor", "blue")
    # Make click-through
    region_border_window.update_idletasks()
    hwnd = win32gui.FindWindow(None, region_border_window.title())
    style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE,
                           style | win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT)
    canvas = tk.Canvas(region_border_window, bg="blue", highlightthickness=0)
    canvas.pack(fill="both", expand=True)
    border_color = "#FFD700"
    border_width = 2
    canvas.create_rectangle(
        border_width // 2, border_width // 2,
        width - border_width // 2, height - border_width // 2,
        outline=border_color, width=border_width
    )
    region_border_window.lift()

def hide_region_border():
    global region_border_window
    if region_border_window and region_border_window.winfo_exists():
        region_border_window.destroy()
        region_border_window = None

def toggle_region_border(icon=None, item=None):
    global region_border_enabled
    region_border_enabled = not region_border_enabled
    if region_border_enabled:
        show_region_border()
    else:
        hide_region_border()

# === STATUS UPDATE ===

def set_status(msg, temporary=False):
    global status_label
    try:
        if status_label and status_label.winfo_exists():
            status_label.config(text=msg)
            if temporary:
                def reset():
                    if status_label and status_label.winfo_exists():
                        status_label.config(text="Translating..." if enabled else "Paused")
                status_label.after(2100, reset)
    except Exception as e:
        log_error(f"set_status error: {e}")

def animate_busy_status():
    global busy_anim_running, busy_anim_dots
    if not busy_anim_running:
        return
    dots = "." * (1 + (busy_anim_dots % 3))
    set_status(f"Translating{dots}")
    busy_anim_dots = (busy_anim_dots + 1) % 3
    try:
        if status_label and status_label.winfo_exists():
            status_label.after(400, animate_busy_status)
    except Exception as e:
        log_error(f"animate_busy_status error: {e}")

def start_busy_animation():
    global busy_anim_running, busy_anim_dots
    busy_anim_running = True
    busy_anim_dots = 0
    animate_busy_status()

def stop_busy_animation():
    global busy_anim_running
    busy_anim_running = False
    set_status("Translating..." if enabled else "Paused")

# === UTIL ===

def _sanitize_text(text):
    lines = [line.rstrip() for line in text.strip().splitlines()]
    new_lines = []
    prev_blank = False
    for line in lines:
        if line.strip() == "":
            if not prev_blank:
                new_lines.append("")
            prev_blank = True
        else:
            new_lines.append(line)
            prev_blank = False
    return "\n".join(new_lines)

def _get_fitting_font_size(text, width, height, min_size=8, max_size=32, font_name="Arial"):
    test_root = tk.Tk()
    test_root.withdraw()
    for size in reversed(range(min_size, max_size+1)):
        font = (font_name, size)
        label = tk.Label(test_root, text=text, font=font, wraplength=width, justify="left")
        label.update_idletasks()
        req_width = label.winfo_reqwidth()
        req_height = label.winfo_reqheight()
        label.destroy()
        if req_width <= width and req_height <= height:
            test_root.destroy()
            return size
    test_root.destroy()
    return min_size

def _get_text_bbox(text, font, max_width=None):
    test_root = tk.Tk()
    test_root.withdraw()
    label = tk.Label(test_root, text=text, font=font, wraplength=max_width, justify="left")
    label.update_idletasks()
    w, h = label.winfo_reqwidth(), label.winfo_reqheight()
    label.destroy()
    test_root.destroy()
    return w, h

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
    global move_mode
    move_mode = True
    overlay_window._drag_start_x = event.x
    overlay_window._drag_start_y = event.y
    set_overlay_clickthrough(False)
    set_status("Moving overlay...", temporary=True)

def do_move(event):
    global overlay_position
    if not move_mode: return
    x = overlay_window.winfo_x() + event.x - overlay_window._drag_start_x
    y = overlay_window.winfo_y() + event.y - overlay_window._drag_start_y
    overlay_window.geometry(f"+{x}+{y}")
    overlay_position = (x, y)
    if header_window:
        hx = x
        hy = y - header_window.winfo_height()
        header_window.geometry(f"+{hx}+{max(0, hy)}")

def end_move(event):
    global overlay_position
    if not move_mode:
        return
    x = overlay_window.winfo_x()
    y = overlay_window.winfo_y()
    overlay_position = (x, y)
    log_action(f"Overlay moved to ({x}, {y}) by mouse drag")
    disable_overlay_drag_mode()


def update_overlay_drag_bindings():
    if overlay_window and overlay_window.winfo_exists() and overlay_label:
        overlay_label.unbind('<Button-1>')
        overlay_label.unbind('<B1-Motion>')
        overlay_label.unbind('<ButtonRelease-1>')
        overlay_window.unbind('<Button-1>')
        overlay_window.unbind('<B1-Motion>')
        overlay_window.unbind('<ButtonRelease-1>')
        overlay_label.bind('<Button-1>', start_move)
        overlay_label.bind('<B1-Motion>', do_move)
        overlay_label.bind('<ButtonRelease-1>', end_move)
        overlay_label.config(cursor="fleur")

# === HEADER WINDOW ===

def enable_overlay_drag_mode():
    if overlay_window and overlay_window.winfo_exists():
        set_overlay_clickthrough(False)
        update_overlay_drag_bindings()
        overlay_window.config(cursor="fleur")
        if overlay_label:
            overlay_label.config(cursor="fleur")
        set_status("Drag overlay to move", temporary=True)
        if hasattr(enable_overlay_drag_mode, 'timer_id'):
            overlay_window.after_cancel(enable_overlay_drag_mode.timer_id)
        enable_overlay_drag_mode.timer_id = overlay_window.after(5000, disable_overlay_drag_mode)

def disable_overlay_drag_mode():
    if overlay_window and overlay_window.winfo_exists():
        set_overlay_clickthrough(True)
        update_overlay_drag_bindings()
        overlay_window.config(cursor="")
        if overlay_label:
            overlay_label.config(cursor="")
        set_status("Translating..." if enabled else "Paused")

def show_header_window(x, y, width):
    global header_window, status_label, menu_btn
    if header_window and header_window.winfo_exists():
        header_window.geometry(f"{width}x36+{x}+{max(0, y-36)}")
        return
    header_window = tk.Toplevel(main_root)
    header_window.title("L2T Overlay Header")
    header_window.geometry(f"{width}x36+{x}+{max(0, y-36)}")
    header_window.wm_attributes("-topmost", True)
    header_window.attributes("-alpha", 0.94)
    header_window.overrideredirect(True)
    header_window.configure(bg="#221b23")
    status_label = tk.Label(header_window, text="Translating..." if enabled else "Paused", font=("Arial", 10, "bold"),
        fg="white", bg="#221b23", anchor="w")
    status_label.pack(side="left", padx=(8,0), pady=2, fill="x", expand=True)
    menu_btn = tk.Button(header_window, text="☰", font=("Arial", 13, "bold"),
        bg="#221b23", fg="#ffd700", bd=0, relief="flat", cursor="hand2")
    menu_btn.pack(side="right", padx=(0,7), pady=2)
    def show_overlay_menu(event=None):
        enable_overlay_drag_mode()
        menu = tk.Menu(header_window, tearoff=0)
        menu.add_command(label="Toggle On/Off", command=lambda: toggle_enabled(None, None))
        menu.add_command(label="Snap Overlay Back", command=lambda: snap_overlay_back())
        menu.add_separator()
        menu.add_command(label="Reselect Region", command=lambda: main_root.after(0, reselect_region))
        menu.add_command(label="Font Size: Auto", command=lambda: set_font_mode_auto(None, None))
        menu.add_command(label="Font Size: Small (9)", command=lambda: set_font_size_fixed(9)(None, None))
        menu.add_command(label="Font Size: Medium (12)", command=lambda: set_font_size_fixed(12)(None, None))
        menu.add_command(label="Font Size: Large (16)", command=lambda: set_font_size_fixed(16)(None, None))
        menu.add_separator()
        menu.add_command(label="Border: None", command=lambda: set_border_mode("none"))
        menu.add_command(label="Border: Thin", command=lambda: set_border_mode("thin"))
        menu.add_separator()
        menu.add_checkbutton(label="Show Region Border", command=toggle_region_border, onvalue=True, offvalue=False, variable=tk.BooleanVar(value=region_border_enabled))
        menu.add_separator()
        menu.add_command(label="Scan Interval: 1s", command=lambda: set_scan_interval(0)(None, None))
        menu.add_command(label="Scan Interval: 2s", command=lambda: set_scan_interval(1)(None, None))
        menu.add_command(label="Scan Interval: 5s", command=lambda: set_scan_interval(2)(None, None))
        menu.add_command(label="Scan Interval: 10s", command=lambda: set_scan_interval(3)(None, None))
        menu.add_command(label="Scan Interval: 30s", command=lambda: set_scan_interval(4)(None, None))
        menu.add_separator()
        menu.add_command(label="View Logs", command=lambda: view_logs(None, None))
        menu.add_command(label="Show Last Error", command=lambda: show_last_error(None, None))
        menu.add_command(label="Test Overlay", command=lambda: test_overlay(None, None))
        menu.add_separator()
        menu.add_command(label="Help / Instructions", command=lambda: show_help(None, None))
        menu.add_command(label="Exit", command=lambda: quit_app(None, None))
        try:
            menu.tk_popup(header_window.winfo_x()+header_window.winfo_width()-50, header_window.winfo_y()+30)
        finally:
            menu.grab_release()
    menu_btn.config(command=show_overlay_menu)

def update_header_window(x, y, width):
    if header_window and header_window.winfo_exists():
        header_window.geometry(f"{width}x36+{x}+{max(0, y-36)}")

def hide_header_window():
    global header_window
    if header_window and header_window.winfo_exists():
        header_window.withdraw()

# === SNAP BACK ===

def snap_overlay_back(icon=None, item=None):
    global overlay_position, capture_region, overlay_window
    if capture_region and overlay_window:
        x1, y1, x2, y2 = capture_region
        overlay_position = None
        width = x2 - x1
        height = y2 - y1
        overlay_window.geometry(f"{width}x{height}+{x1}+{y1}")
        update_header_window(x1, y1, width)
        set_status("Overlay snapped back", temporary=True)
        log_action(f"Overlay snapped back to ({x1},{y1})")
    else:
        set_status("Snap back failed", temporary=True)
        log_action("Snap back failed: overlay or region missing")

# === BORDER CONFIG ===

def set_border_mode(mode):
    global border_mode
    border_mode = mode
    show_translation("")

# === TRANSLATION / OCR with TIMEOUT ===

def translate_text_google(text):
    try:
        result = translator.translate(text, src="ru", dest="en")
        return result.text
    except Exception as e:
        log_error(f"Translation error: {e}")
        set_status("Translation Error", temporary=True)
        return f"[Translation Error] {e}"

def ocr_worker(image):
    try:
        return pytesseract.image_to_string(image, lang="rus+eng")
    except Exception as e:
        log_error(f"OCR error: {e}")
        set_status("OCR Error", temporary=True)
        return "[OCR Error]"

def get_text_from_chat():
    if not capture_region:
        return ""
    try:
        start_busy_animation()
        if overlay_label and overlay_label.winfo_exists():
            overlay_label.config(text="")
        image = ImageGrab.grab(bbox=capture_region)
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(ocr_worker, image)
            try:
                text = future.result(timeout=3)
            except concurrent.futures.TimeoutError:
                log_error("OCR timed out (stuck on image_to_string).")
                set_status("OCR Timeout – retrying", temporary=True)
                text = "[OCR Timeout]"
        stop_busy_animation()
        return text
    except Exception as e:
        log_error(f"OCR error: {e}")
        stop_busy_animation()
        set_status("OCR Error", temporary=True)
        return ""

# === OVERLAY DRAW/UPDATE ===

def _show_translation_tk(text):
    global overlay_window, overlay_label, overlay_position, current_font_size, font_mode, status_label, menu_btn, header_window
    try:
        if not enabled:
            log_action("Overlay not shown (disabled)")
            if overlay_window:
                overlay_window.withdraw()
            hide_header_window()
            hide_region_border()
            return

        x1, y1, x2, y2 = capture_region
        region_width = x2 - x1
        region_height = y2 - y1

        text = _sanitize_text(text)

        if font_mode == "auto":
            best_font_size = _get_fitting_font_size(text, region_width-10, region_height-8)
            font = ("Arial", best_font_size)
            overlay_width, overlay_height = region_width, region_height
        else:
            font = ("Arial", current_font_size)
            overlay_width, overlay_height = _get_text_bbox(text, font)
            overlay_width += 10
            overlay_height += 8

        if overlay_position is not None:
            ox, oy = overlay_position
        else:
            ox, oy = x1, y1

        create_new = (overlay_window is None or not overlay_window.winfo_exists())
        if create_new:
            overlay_window = tk.Toplevel(main_root)
            overlay_window.title("Translation")
            overlay_window.geometry(f"{overlay_width}x{overlay_height}+{ox}+{oy}")
            overlay_window.wm_attributes("-topmost", True)
            overlay_window.attributes("-alpha", 0.88)
            overlay_window.configure(bg="black")
            overlay_window.overrideredirect(True)
            if border_mode == "thin":
                overlay_window.configure(highlightthickness=2, highlightbackground="#ffd700")
            else:
                overlay_window.configure(highlightthickness=0)

            overlay_label = tk.Label(
                overlay_window,
                text=text,
                font=font,
                bg="black",
                fg="yellow",
                justify="left",
                anchor="nw",
                wraplength=overlay_width-8
            )
            overlay_label.pack(fill="both", expand=True, padx=5, pady=5)

            set_overlay_clickthrough(True)
            update_overlay_drag_bindings()
            log_action("Created overlay window")
        else:
            overlay_window.geometry(f"{overlay_width}x{overlay_height}+{ox}+{oy}")
            if border_mode == "thin":
                overlay_window.configure(highlightthickness=2, highlightbackground="#ffd700")
            else:
                overlay_window.configure(highlightthickness=0)
            overlay_label.config(font=font, wraplength=overlay_width-8)

        overlay_label.config(text=text)
        overlay_window.deiconify()
        overlay_window.lift()
        set_overlay_clickthrough(True)
        update_overlay_drag_bindings()

        show_header_window(ox, oy, overlay_width)
        header_window.deiconify()
        header_window.lift()

        # SHOW OR UPDATE REGION BORDER BOX
        if region_border_enabled:
            show_region_border()
        else:
            hide_region_border()
    except Exception:
        log_error(traceback.format_exc())

def show_translation(text):
    main_root.after(0, _show_translation_tk, text)

def hide_overlay():
    global overlay_window
    if overlay_window:
        overlay_window.withdraw()
        hide_header_window()
    hide_region_border()

# === MONITOR/LOOP ===

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

# === REGION SELECTOR ===

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
        set_status("Region updated", temporary=True)
        log_action(f"Selected region: {region}")

    def on_escape(event):
        log_error("User canceled region selection.")
        set_status("Region selection canceled", temporary=True)
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
        set_status("Region updated", temporary=True)
        log_action(f"Region set to {capture_region}")
        show_region_border()
    else:
        hide_region_border()

def reselect_region():
    global capture_region, overlay_window, overlay_position
    log_action("Reselect region initiated (tray/menu)")
    capture_region = None
    overlay_position = None
    if overlay_window:
        overlay_window.withdraw()
    select_region()
    log_action("Region reselected by user.")
    show_translation("")

# === SYSTEM TRAY ===

def toggle_enabled(icon, item):
    global enabled, overlay_window
    enabled = not enabled
    set_status("Paused" if not enabled else "Translating...", temporary=True)
    log_action(f"Toggled all: {'ON' if enabled else 'OFF'} (tray/menu)")
    if not enabled:
        hide_overlay()

def set_font_mode_auto(icon, item):
    global font_mode
    font_mode = "auto"
    set_status("Font: Auto-fit", temporary=True)
    show_translation("")

def set_font_size_fixed(size):
    def handler(icon, item):
        global current_font_size, font_mode
        font_mode = "fixed"
        current_font_size = size
        set_status(f"Font size: {size}", temporary=True)
        show_translation("")
    return handler

def set_scan_interval(idx):
    def handler(icon, item):
        global scan_interval_idx
        scan_interval_idx = idx
        set_status(f"Scan interval: {SCAN_INTERVALS[idx]}s", temporary=True)
        log_action(f"Scan interval set to {SCAN_INTERVALS[idx]}s")
    return handler

def set_border_mode_tray(mode):
    def handler(icon, item):
        set_border_mode(mode)
    return handler

def view_logs(icon, item):
    log_action("Opened logs via tray")
    set_status("Opening logs.txt", temporary=True)
    log_file = os.path.join(os.path.dirname(sys.argv[0]), "logs.txt")
    try:
        os.startfile(log_file)
    except Exception as e:
        log_error(f"Could not open logs: {e}")
        set_status("Failed to open logs", temporary=True)

def show_last_error(icon, item):
    global last_error
    log_action("Show last error tray item selected")
    set_status("Showed last error", temporary=True)
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
    set_status("Test overlay", temporary=True)
    show_translation("Test overlay\nThis is a sample translation box.")

def show_help(icon, item):
    main_root.after(0, show_help_window)

def quit_app(icon=None, item=None):
    log_action("Exiting app via tray/menu")
    set_status("Exiting...", temporary=True)
    try:
        if icon is not None:
            icon.stop()
    except Exception:
        pass
    os._exit(0)

def setup_tray():
    font_menu = pystray.Menu(
        pystray.MenuItem("Auto-fit", set_font_mode_auto),
        pystray.MenuItem("Small (9)", set_font_size_fixed(9)),
        pystray.MenuItem("Medium (12)", set_font_size_fixed(12)),
        pystray.MenuItem("Large (16)", set_font_size_fixed(16))
    )
    border_menu = pystray.Menu(
        pystray.MenuItem("None", set_border_mode_tray("none")),
        pystray.MenuItem("Thin", set_border_mode_tray("thin")),
    )
    overlay_menu = pystray.Menu(
        pystray.MenuItem("Toggle On/Off", toggle_enabled),
        pystray.MenuItem("Snap Overlay Back", snap_overlay_back),
        pystray.MenuItem("Font Size", font_menu),
        pystray.MenuItem("Border", border_menu),
        pystray.MenuItem("Show Region Border", toggle_region_border, checked=lambda item: region_border_enabled)
    )
    scan_menu = pystray.Menu(
        pystray.MenuItem("1s (Fast)", set_scan_interval(0)),
        pystray.MenuItem("2s", set_scan_interval(1)),
        pystray.MenuItem("5s (Default)", set_scan_interval(2)),
        pystray.MenuItem("10s", set_scan_interval(3)),
        pystray.MenuItem("30s (Slow)", set_scan_interval(4))
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
                generate_tray_icon(),
                "L2 Chat Translator",
                menu=pystray.Menu(
                    pystray.MenuItem("Overlay", overlay_menu),
                    pystray.MenuItem("Reselect Region", lambda icon, item: main_root.after(0, reselect_region)),
                    pystray.MenuItem("Scan", scan_menu),
                    pystray.MenuItem("Diagnostics", diagnostics_menu),
                    pystray.MenuItem("Help / Instructions", show_help),
                    pystray.MenuItem("Exit", quit_app)
                )
            )
            icon.run()
        except Exception:
            log_error(traceback.format_exc())

    threading.Thread(target=tray_thread, daemon=True).start()
    log_action("System tray setup complete")

# === HELP ===

def show_help_window():
    log_action("Help window opened")
    help_win = tk.Toplevel(main_root)
    help_win.title("L2T Overlay Help / Instructions")
    help_win.geometry("730x660+400+120")
    help_win.configure(bg="#222")
    text = tk.Text(help_win, font=("Arial", 13), bg="#222", fg="white", wrap="word")
    text.insert("1.0", HELP_TEXT.strip())
    text.config(state="disabled")
    text.pack(padx=16, pady=16, fill="both", expand=True)
    tk.Button(help_win, text="Close", font=("Arial", 12), command=help_win.destroy).pack(pady=8)
    help_win.lift()

# === MAIN ===

if __name__ == "__main__":
    ctypes.windll.user32.SetProcessDPIAware()
    log_action("App started")
    select_region()

    if capture_region:
        show_region_border()
        start_monitoring()
        setup_tray()
        main_root.mainloop()
    else:
        log_action("No region selected. Exiting.")
