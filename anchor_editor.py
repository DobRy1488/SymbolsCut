import os
import json
from tkinter import (
    Tk, Canvas, Button, Frame, Label,
    filedialog, Entry, LEFT, RIGHT, BOTH, X
)
from PIL import Image, ImageTk


class AnchorEditor:

    def __init__(self, root):
        self.root = root
        self.root.title("Anchor Editor")

        self.font_dir = None
        self.letters = []
        self.index = 0
        self.anchors = {}

        self.current_image = None
        self.tk_image = None

        self.setup_ui()

    # ===============================
    # UI
    # ===============================

    def setup_ui(self):
        top = Frame(self.root)
        top.pack(fill=X)

        Button(top, text="Файл", command=self.choose_folder).pack(side=LEFT, padx=5, pady=5)

        self.letter_entry = Entry(top, width=10, justify="center")
        self.letter_entry.pack(side=LEFT, padx=20)
        self.letter_entry.bind("<Return>", self.jump_to_letter)

        Button(top, text="Сохранить", command=self.save_anchors).pack(side=RIGHT, padx=5, pady=5)

        self.canvas = Canvas(self.root, bg="#dddddd", width=800, height=600)
        self.canvas.pack(fill=BOTH, expand=True)

        self.canvas.bind("<Button-1>", self.set_entry_anchor)
        self.canvas.bind("<Button-3>", self.set_exit_anchor)

        bottom = Frame(self.root)
        bottom.pack(fill=X)

        Button(bottom, text="←", command=self.prev_letter, width=10).pack(side=LEFT, padx=10, pady=5)
        Button(bottom, text="→", command=self.next_letter, width=10).pack(side=RIGHT, padx=10, pady=5)

    # ===============================
    # Загрузка шрифта
    # ===============================

    def choose_folder(self):
        folder = filedialog.askdirectory()
        if not folder:
            return

        self.font_dir = folder
        self.load_letters()
        self.load_existing_anchors()

        self.index = 0
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

    # ===============================
    # Отображение буквы
    # ===============================

    def show_letter(self):
        if not self.letters:
            return

        letter = self.letters[self.index]
        self.letter_entry.delete(0, "end")
        self.letter_entry.insert(0, letter["name"])

        img = Image.open(letter["path"]).convert("RGBA")
        self.current_image = img

        self.tk_image = ImageTk.PhotoImage(img)

        self.canvas.delete("all")

        self.canvas.config(
            width=img.width,
            height=img.height
        )

        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image)

        self.draw_existing_anchors()

    def draw_existing_anchors(self):
        name = self.letters[self.index]["name"]

        if name in self.anchors:
            data = self.anchors[name]

            if "entry" in data:
                x, y = data["entry"]
                self.draw_point(x, y, "green")

            if "exit" in data:
                x, y = data["exit"]
                self.draw_point(x, y, "red")

    def draw_point(self, x, y, color):
        r = 5
        self.canvas.create_oval(
            x - r, y - r,
            x + r, y + r,
            fill=color,
            outline=""
        )

    # ===============================
    # Клики мыши
    # ===============================

    def set_entry_anchor(self, event):
        self.set_anchor("entry", event.x, event.y)

    def set_exit_anchor(self, event):
        self.set_anchor("exit", event.x, event.y)

    def set_anchor(self, anchor_type, x, y):
        name = self.letters[self.index]["name"]

        if name not in self.anchors:
            self.anchors[name] = {}

        self.anchors[name][anchor_type] = [x, y]

        self.show_letter()

    # ===============================
    # Навигация
    # ===============================

    def next_letter(self):
        if self.index < len(self.letters) - 1:
            self.index += 1
            self.show_letter()

    def prev_letter(self):
        if self.index > 0:
            self.index -= 1
            self.show_letter()

    def jump_to_letter(self, event=None):
        name = self.letter_entry.get()
        for i, l in enumerate(self.letters):
            if l["name"] == name:
                self.index = i
                self.show_letter()
                break

    # ===============================
    # Сохранение
    # ===============================

    def save_anchors(self):
        if not self.font_dir:
            return

        json_path = os.path.join(self.font_dir, "anchors.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(self.anchors, f, ensure_ascii=False, indent=2)

        print("Якоря сохранены:", json_path)


# ===============================
# Запуск
# ===============================

if __name__ == "__main__":
    root = Tk()
    app = AnchorEditor(root)
    root.mainloop()