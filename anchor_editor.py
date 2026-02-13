import os
import json
from tkinter import (
    Tk, Canvas, Button, Frame,
    filedialog, Entry, LEFT, RIGHT,
    X, Label
)
from PIL import Image, ImageTk, ImageDraw, ImageFilter


WINDOW_WIDTH = 1100
WINDOW_HEIGHT = 820

CANVAS_WIDTH = 1000
CANVAS_HEIGHT = 600


class AnchorEditor:

    def __init__(self, root):
        self.root = root
        self.root.title("Anchor Editor")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.resizable(False, False)

        # ТЕМНАЯ ТЕМА ПО УМОЛЧАНИЮ
        self.dark_mode = True

        self.font_dir = None
        self.letters = []
        self.index = 0
        self.anchors = {}

        self.original_image = None
        self.tk_image = None
        self.glow_images = []

        self.image_offset = [0, 0]

        self.scale = 1.0
        self.min_scale = 0.2
        self.max_scale = 5.0

        self.setup_ui()
        self.apply_theme()

    # ================= UI =================

    def setup_ui(self):

        self.top = Frame(self.root)
        self.top.pack(fill=X)

        Button(self.top, text="Открыть папку",
               command=self.choose_folder).pack(side=LEFT, padx=10, pady=10)

        Button(self.top, text="Сохранить",
               command=self.save_anchors).pack(side=LEFT, padx=10)

        # Переключатель темы
        self.theme_frame = Frame(self.top)
        self.theme_frame.pack(side=RIGHT, padx=20)

        self.moon_label = Label(self.theme_frame, text="🌙", font=("Arial", 14))
        self.moon_label.pack(side=LEFT)

        self.toggle_canvas = Canvas(
            self.theme_frame,
            width=80,
            height=30,
            highlightthickness=0,
            bd=0
        )
        self.toggle_canvas.pack(side=LEFT, padx=5)
        self.toggle_canvas.bind("<Button-1>", self.toggle_theme)

        self.sun_label = Label(self.theme_frame, text="☀", font=("Arial", 14))
        self.sun_label.pack(side=LEFT)

        # Canvas буквы
        self.canvas = Canvas(
            self.root,
            width=CANVAS_WIDTH,
            height=CANVAS_HEIGHT,
            highlightthickness=0
        )
        self.canvas.pack(pady=10)

        self.canvas.bind("<Button-1>", self.set_entry_anchor)
        self.canvas.bind("<Button-3>", self.set_exit_anchor)
        self.canvas.bind("<MouseWheel>", self.zoom)

        # Низ
        self.bottom = Frame(self.root)
        self.bottom.pack(fill=X)

        self.prev_button = Button(
            self.bottom,
            text="←",
            command=self.prev_letter,
            font=("Arial", 32, "bold"),
            width=5,
            height=2
        )
        self.prev_button.pack(side=LEFT, padx=40, pady=10)

        self.letter_entry = Entry(
            self.bottom,
            width=8,
            font=("Arial", 26),
            justify="center"
        )
        self.letter_entry.pack(side=LEFT, expand=True, ipady=18)
        self.letter_entry.bind("<Return>", self.jump_to_letter)

        self.next_button = Button(
            self.bottom,
            text="→",
            command=self.next_letter,
            font=("Arial", 32, "bold"),
            width=5,
            height=2
        )
        self.next_button.pack(side=RIGHT, padx=40, pady=10)

        self.root.bind("<Left>", lambda e: self.prev_letter())
        self.root.bind("<Right>", lambda e: self.next_letter())

    # ================= ТЕМА =================

    def toggle_theme(self, event=None):
        self.dark_mode = not self.dark_mode
        self.apply_theme()

    def draw_toggle(self):

        self.toggle_canvas.delete("all")

        if self.dark_mode:
            track_color = "#444444"      # тёмно-серая подложка
            knob_color = "#666666"       # серый ползунок
            knob_x = 5                   # СЛЕВА
        else:
            track_color = "#cccccc"
            knob_color = "#ffffff"
            knob_x = 45                  # СПРАВА

        # подложка
        self.toggle_canvas.create_rectangle(
            10, 12, 70, 18,
            fill=track_color,
            outline=""
        )

        # квадрат
        self.toggle_canvas.create_rectangle(
            knob_x, 5,
            knob_x + 28, 25,
            fill=knob_color,
            outline=""
        )

    def apply_theme(self):

        if self.dark_mode:
            bg = "#1e1e1e"
            panel = "#2a2a2a"
            fg = "#ffffff"
            button_bg = "#333333"
            entry_bg = "#2a2a2a"
        else:
            bg = "#f5f5f5"
            panel = "#ffffff"
            fg = "#000000"
            button_bg = "#dddddd"
            entry_bg = "#ffffff"

        self.root.configure(bg=bg)
        self.top.configure(bg=panel)
        self.bottom.configure(bg=panel)
        self.canvas.configure(bg=panel)
        self.theme_frame.configure(bg=panel)
        self.toggle_canvas.configure(bg=panel)

        self.moon_label.configure(bg=panel, fg=fg)
        self.sun_label.configure(bg=panel, fg=fg)

        for widget in self.top.winfo_children():
            if isinstance(widget, Button):
                widget.configure(bg=button_bg, fg=fg)

        for widget in self.bottom.winfo_children():
            if isinstance(widget, Button):
                widget.configure(bg=button_bg, fg=fg)

        self.letter_entry.configure(bg=entry_bg, fg=fg, insertbackground=fg)

        self.draw_toggle()

    # ================= ЯРКИЙ GLOW =================

    def create_glow_image(self, color):

        size = 70
        center = size // 2
        radius = 24

        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        pixels = img.load()

        r_col, g_col, b_col, _ = color

        for y in range(size):
            for x in range(size):
                dx = x - center
                dy = y - center
                dist = (dx * dx + dy * dy) ** 0.5

                if dist <= radius:

                    # более агрессивный профиль яркости
                    intensity = 1 - (dist / radius)

                    # делаем центр намного ярче
                    intensity = intensity ** 2.4

                    # усиливаем цвет
                    boost = 2.2
                    r = min(255, int(r_col * intensity * boost))
                    g = min(255, int(g_col * intensity * boost))
                    b = min(255, int(b_col * intensity * boost))

                    alpha = min(255, int(255 * intensity * 1.6))

                    pixels[x, y] = (r, g, b, alpha)

        # лёгкое bloom-размытие
        img = img.filter(ImageFilter.GaussianBlur(3))

        # МЕНЬШЕ белое ядро
        draw = ImageDraw.Draw(img)
        draw.ellipse(
            (center - 2, center - 2,
            center + 2, center + 2),
            fill=(255, 255, 255, 255)
        )

        return ImageTk.PhotoImage(img)

    def draw_existing_anchors(self):

        name = self.letters[self.index]["name"]
        if name not in self.anchors:
            return

        x_offset, y_offset = self.image_offset
        data = self.anchors[name]

        self.glow_images = []

        for t, color in [("entry", (0, 255, 0, 255)),
                         ("exit", (255, 0, 0, 255))]:

            if t in data:
                x, y = data[t]
                x = x * self.scale + x_offset
                y = y * self.scale + y_offset

                glow = self.create_glow_image(color)
                self.glow_images.append(glow)

                self.canvas.create_image(x, y, image=glow)

    # ================= Остальной функционал =================

    def choose_folder(self):
        folder = filedialog.askdirectory()
        if not folder:
            return

        self.font_dir = folder
        self.load_letters()
        self.load_existing_anchors()

        self.index = 0
        self.scale = 1.0
        self.show_letter()

    def load_letters(self):
        self.letters = []
        for f in sorted(os.listdir(self.font_dir)):
            if f.lower().endswith(".png"):
                name = os.path.splitext(f)[0]
                path = os.path.join(self.font_dir, f)
                self.letters.append({"name": name, "path": path})

    def load_existing_anchors(self):
        json_path = os.path.join(self.font_dir, "anchors.json")
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                self.anchors = json.load(f)
        else:
            self.anchors = {}

    def show_letter(self):

        if not self.letters:
            return

        letter = self.letters[self.index]

        self.letter_entry.delete(0, "end")
        self.letter_entry.insert(0, letter["name"])

        self.canvas.delete("all")

        img = Image.open(letter["path"]).convert("RGBA")
        self.original_image = img

        scaled = img.resize(
            (int(img.width * self.scale),
             int(img.height * self.scale)),
            Image.LANCZOS
        )

        self.tk_image = ImageTk.PhotoImage(scaled)

        # если первый раз — центрируем
        if self.image_offset == [0, 0]:
            self.image_offset[0] = (CANVAS_WIDTH - scaled.width) // 2
            self.image_offset[1] = (CANVAS_HEIGHT - scaled.height) // 2

        x_offset, y_offset = self.image_offset

        self.canvas.create_image(
            x_offset,
            y_offset,
            anchor="nw",
            image=self.tk_image
        )

        self.draw_existing_anchors()

    def set_entry_anchor(self, event):
        self.set_anchor("entry", event)

    def set_exit_anchor(self, event):
        self.set_anchor("exit", event)

    def set_anchor(self, anchor_type, event):

        if not self.original_image:
            return

        name = self.letters[self.index]["name"]
        x_offset, y_offset = self.image_offset

        real_x = (event.x - x_offset) / self.scale
        real_y = (event.y - y_offset) / self.scale

        if 0 <= real_x <= self.original_image.width and \
           0 <= real_y <= self.original_image.height:

            if name not in self.anchors:
                self.anchors[name] = {}

            self.anchors[name][anchor_type] = [
                float(real_x),
                float(real_y)
            ]

            self.show_letter()

    def next_letter(self):
        if self.index < len(self.letters) - 1:
            self.index += 1
            self.scale = 1.0
            self.image_offset = [0, 0]
            self.show_letter()

    def prev_letter(self):
        if self.index > 0:
            self.index -= 1
            self.scale = 1.0
            self.image_offset = [0, 0]
            self.show_letter()

    def jump_to_letter(self, event=None):
        name = self.letter_entry.get()
        for i, l in enumerate(self.letters):
            if l["name"] == name:
                self.index = i
                self.scale = 1.0
                self.show_letter()
                break

    def zoom(self, event):

        if not self.original_image:
            return

        old_scale = self.scale

        # Определяем направление zoom
        if event.delta > 0:
            self.scale *= 1.1
        else:
            self.scale /= 1.1

        self.scale = max(self.min_scale, min(self.scale, self.max_scale))

        scale_ratio = self.scale / old_scale

        # Координаты мыши
        mouse_x = event.x
        mouse_y = event.y

        # Пересчёт смещения
        self.image_offset[0] = mouse_x - scale_ratio * (mouse_x - self.image_offset[0])
        self.image_offset[1] = mouse_y - scale_ratio * (mouse_y - self.image_offset[1])

        self.show_letter()

    def save_anchors(self):

        if not self.font_dir:
            return

        json_path = os.path.join(self.font_dir, "anchors.json")

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(self.anchors, f, ensure_ascii=False, indent=2)

        print("Якоря сохранены:", json_path)


if __name__ == "__main__":
    root = Tk()
    app = AnchorEditor(root)
    root.mainloop()