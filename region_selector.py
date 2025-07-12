from PIL import ImageGrab, Image, ImageTk, ImageDraw
import tkinter as tk
from log_utils import log_action, log_error

def select_region(main_root):
    region = []
    root = tk.Toplevel(main_root)
    root.attributes("-fullscreen", True)
    root.attributes("-alpha", 1.0)
    root.configure(bg='black')
    root.title("Select Chat Region")

    try:
        screen_image = ImageGrab.grab()
    except Exception as e:
        log_error(f"Could not grab screen for selection: {e}")
        screen_image = Image.new("RGB", (1920, 1080), "black")

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
    root.bind("<Escape>", on_escape)
    root.grab_set()
    main_root.wait_window(root)

    if region:
        log_action(f"Region set to {tuple(region)}")
        return tuple(region)
    else:
        log_action("Region selection canceled")
        return None
