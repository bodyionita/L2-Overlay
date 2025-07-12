import tkinter as tk
import win32gui
import win32con
from log_utils import log_action

class Overlay:
    def __init__(self, main_root, get_capture_region, font_size=12):
        self.main_root = main_root
        self.get_capture_region = get_capture_region
        self.font_size = font_size
        self.overlay_window = None
        self.overlay_label = None
        self.overlay_position = None  # (x, y) if moved
        self.move_mode = False

    def set_clickthrough(self, enable):
        if self.overlay_window and self.overlay_window.winfo_exists():
            self.overlay_window.update_idletasks()
            hwnd = win32gui.FindWindow(None, self.overlay_window.title())
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            if enable:
                style = style | win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT
            else:
                style = (style | win32con.WS_EX_LAYERED) & ~win32con.WS_EX_TRANSPARENT
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, style)

    def update_drag_bindings(self):
        if self.overlay_window and self.overlay_window.winfo_exists():
            self.overlay_label.unbind('<Button-1>')
            self.overlay_label.unbind('<B1-Motion>')
            self.overlay_label.unbind('<ButtonRelease-1>')
            self.overlay_window.unbind('<Button-1>')
            self.overlay_window.unbind('<B1-Motion>')
            self.overlay_window.unbind('<ButtonRelease-1>')
            if self.move_mode:
                self.overlay_label.bind('<Button-1>', self.start_move)
                self.overlay_label.bind('<B1-Motion>', self.do_move)
                self.overlay_label.bind('<ButtonRelease-1>', self.end_move)
                self.overlay_window.bind('<Button-1>', self.start_move)
                self.overlay_window.bind('<B1-Motion>', self.do_move)
                self.overlay_window.bind('<ButtonRelease-1>', self.end_move)
                self.overlay_label.config(cursor="fleur")
            else:
                self.overlay_label.config(cursor="")

    def show(self, text):
        region = self.get_capture_region()
        if not region:
            return
        x1, y1, x2, y2 = region
        width, height = x2 - x1, y2 - y1
        ox, oy = self.overlay_position if self.overlay_position else (x1, y1)
        create_new = (self.overlay_window is None or not self.overlay_window.winfo_exists())

        if create_new:
            self.overlay_window = tk.Toplevel(self.main_root)
            self.overlay_window.title("Translation")
            self.overlay_window.geometry(f"{width}x{height}+{ox}+{oy}")
            self.overlay_window.wm_attributes("-topmost", True)
            self.overlay_window.attributes("-alpha", 0.7)
            self.overlay_window.configure(bg="black")
            self.overlay_window.overrideredirect(True)

            self.overlay_label = tk.Label(
                self.overlay_window,
                text=text,
                font=("Arial", self.font_size),
                bg="black",
                fg="yellow",
                justify="left",
                anchor="nw"
            )
            self.overlay_label.pack(fill="both", expand=True, padx=5, pady=5)
            self.set_clickthrough(True)
            self.update_drag_bindings()
            log_action("Created overlay window")
        else:
            self.overlay_window.geometry(f"{width}x{height}+{ox}+{oy}")

        self.overlay_label.config(text=text, font=("Arial", self.font_size))
        self.overlay_window.deiconify()
        self.overlay_window.lift()
        self.set_clickthrough(not self.move_mode)
        self.update_drag_bindings()
        log_action("Updated overlay with new translation")

    def hide(self):
        if self.overlay_window:
            self.overlay_window.withdraw()

    def snap_back(self):
        region = self.get_capture_region()
        if region and self.overlay_window:
            x1, y1, x2, y2 = region
            self.overlay_position = None
            width = x2 - x1
            height = y2 - y1
            self.overlay_window.geometry(f"{width}x{height}+{x1}+{y1}")
            log_action(f"Overlay snapped back to ({x1},{y1})")
        else:
            log_action("Snap back failed: overlay or region missing")

    def set_font_size(self, size):
        self.font_size = size
        if self.overlay_label:
            self.overlay_label.config(font=("Arial", self.font_size))

    # Drag and move handlers (for move_mode)
    def start_move(self, event):
        if not self.move_mode: return
        self.overlay_window._drag_start_x = event.x
        self.overlay_window._drag_start_y = event.y

    def do_move(self, event):
        if not self.move_mode: return
        x = self.overlay_window.winfo_x() + event.x - self.overlay_window._drag_start_x
        y = self.overlay_window.winfo_y() + event.y - self.overlay_window._drag_start_y
        self.overlay_window.geometry(f"+{x}+{y}")
        self.overlay_position = (x, y)

    def end_move(self, event):
        if not self.move_mode: return
        x = self.overlay_window.winfo_x()
        y = self.overlay_window.winfo_y()
        self.overlay_position = (x, y)
        log_action(f"Overlay moved to ({x}, {y}) by mouse drag")

    def set_move_mode(self, mode):
        self.move_mode = mode
        self.set_clickthrough(not mode)
        self.update_drag_bindings()
