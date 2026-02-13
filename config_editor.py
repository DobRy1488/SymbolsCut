import tkinter as tk
from tkinter import filedialog, Menu
from PIL import Image, ImageTk
import os


class HandFontEditor(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Hand Font Scale Editor")
        self.geometry("1300x750")
        self.configure(bg="#1e1e1e")

        # --------- STATE ---------
        self.font_folder = None
        self.letters = {}
        self.word = "Привет"
        self.show_black = True

        self.max_scale = 1.0
        self.min_scale = 1.0
        self.line_spacing = 90

        self.build_layout()
        self.draw_scene()

    # =====================================================
    # LAYOUT
    # =====================================================

    def build_layout(self):

        # ---------- TOP BAR ----------
        top = tk.Frame(self, bg="#252525", height=45)
        top.grid(row=0, column=0, columnspan=4, sticky="ew")
        top.grid_propagate(False)

        tk.Button(top, text="Файл", bg="#2c2c2c", fg="white",
                  bd=0, command=self.file_menu).pack(side="left", padx=5)

        tk.Button(top, text="Сохранить", bg="#2c2c2c", fg="white",
                  bd=0, command=self.save_file).pack(side="left", padx=5)

        tk.Button(top, text="Шрифт", bg="#2c2c2c", fg="white",
                  bd=0, command=self.load_font).pack(side="left", padx=5)

        tk.Button(top, text="👁", bg="#2c2c2c", fg="white",
                  bd=0, command=self.toggle_black).pack(side="left", padx=5)

        self.entry = tk.Entry(top, bg="#333333",
                              fg="white", insertbackground="white", bd=0)
        self.entry.insert(0, self.word)
        self.entry.pack(side="left", padx=10)
        self.entry.bind("<KeyRelease>", self.update_word)

        tk.Label(top, text="🌙  ■",
                 bg="#252525", fg="#aaaaaa").pack(side="right", padx=10)

        # ---------- MAIN GRID ----------
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=4)  # canvas
        self.grid_columnconfigure(1, weight=1)  # hints
        self.grid_columnconfigure(2, weight=0)  # sliders
        self.grid_columnconfigure(3, weight=0)  # functions

        # ---------- CANVAS ZONE ----------
        canvas_frame = tk.Frame(self, bg="#1e1e1e")
        canvas_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=20)

        self.canvas = tk.Canvas(canvas_frame,
                                bg="#252525",
                                highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # ---------- HINT ZONE ----------
        hint_frame = tk.Frame(self, bg="#202020", width=200)
        hint_frame.grid(row=1, column=1, sticky="ns", pady=20)

        tk.Label(hint_frame, text="Подсказки",
                 bg="#202020", fg="white").pack(pady=10)

        self.hints = tk.Label(hint_frame,
                              text="Тут будет текст подсказок.",
                              bg="#262626",
                              fg="#aaaaaa",
                              wraplength=180,
                              justify="left")
        self.hints.pack(fill="both", expand=True, padx=10, pady=10)

        # ---------- SLIDERS ----------
        slider_frame = tk.Frame(self, bg="#1e1e1e")
        slider_frame.grid(row=1, column=2, sticky="ns", padx=10)

        tk.Label(slider_frame, text="MAX",
                 bg="#1e1e1e", fg="white").pack()

        self.max_slider = tk.Scale(slider_frame,
                                   from_=0, to=200,
                                   orient="vertical",
                                   bg="#1e1e1e",
                                   fg="white",
                                   troughcolor="#303030",
                                   highlightthickness=0,
                                   command=self.update_max)
        self.max_slider.set(100)
        self.max_slider.pack(pady=10)

        tk.Label(slider_frame, text="MIN",
                 bg="#1e1e1e", fg="white").pack()

        self.min_slider = tk.Scale(slider_frame,
                                   from_=200, to=50,
                                   orient="vertical",
                                   bg="#1e1e1e",
                                   fg="white",
                                   troughcolor="#303030",
                                   highlightthickness=0,
                                   command=self.update_min)
        self.min_slider.set(100)
        self.min_slider.pack(pady=10)

        # ---------- FUNCTION BUTTONS ----------
        func_frame = tk.Frame(self, bg="#1e1e1e")
        func_frame.grid(row=1, column=3, sticky="ns", padx=20)

        for i in range(6):
            tk.Button(func_frame,
                      text=f"F{i+1}",
                      bg="#2c2c2c",
                      fg="white",
                      bd=0,
                      width=6,
                      height=2).pack(pady=10)

        # ---------- BOTTOM BAR ----------
        bottom = tk.Frame(self, bg="#252525", height=55)
        bottom.grid(row=2, column=0, columnspan=4, sticky="ew")
        bottom.grid_propagate(False)

        tk.Button(bottom, text="Пред",
                  bg="#2c2c2c", fg="white",
                  bd=0, width=12).pack(side="left", padx=40, pady=10)

        tk.Button(bottom, text="След",
                  bg="#2c2c2c", fg="white",
                  bd=0, width=12).pack(side="right", padx=40, pady=10)

    # =====================================================
    # FILE
    # =====================================================

    def file_menu(self):
        menu = Menu(self, tearoff=0)
        menu.add_command(label="Создать новый")
        menu.add_command(label="Загрузить")
        menu.post(self.winfo_pointerx(),
                  self.winfo_pointery())

    def save_file(self):
        filedialog.asksaveasfilename(defaultextension=".json")

    # =====================================================
    # FONT
    # =====================================================

    def load_font(self):
        folder = filedialog.askdirectory()
        if not folder:
            return

        self.letters.clear()

        for file in os.listdir(folder):
            if file.endswith(".png"):
                name = file.replace(".png", "")
                path = os.path.join(folder, file)
                img = Image.open(path).convert("RGBA")
                self.letters[name] = img

        self.draw_scene()

    def get_letter_key(self, char):
        return char if char.isupper() else char + "l"

    # =====================================================
    # UPDATE
    # =====================================================

    def update_word(self, event=None):
        self.word = self.entry.get()
        self.draw_scene()

    def toggle_black(self):
        self.show_black = not self.show_black
        self.draw_scene()

    def update_max(self, value):
        self.max_scale = float(value) / 100
        self.draw_scene()

    def update_min(self, value):
        self.min_scale = max(float(value) / 100, 0.5)
        self.draw_scene()

    # =====================================================
    # DRAW
    # =====================================================

    def draw_lines(self):
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()

        baseline = h // 2
        top = baseline - self.line_spacing
        bottom = baseline + self.line_spacing

        # ВСЕ линии синие
        blue = "#3a6ea5"

        self.canvas.create_line(0, top, w, top, fill=blue, width=2)
        self.canvas.create_line(0, baseline, w, baseline, fill=blue, width=3)
        self.canvas.create_line(0, bottom, w, bottom, fill=blue, width=2)

    def draw_word(self, scale):
        x = 100
        baseline = self.canvas.winfo_height() // 2

        for char in self.word:
            key = self.get_letter_key(char)

            if key in self.letters:
                img = self.letters[key]

                target_height = self.line_spacing
                ratio = target_height / img.height
                final_scale = ratio * scale

                new_w = int(img.width * final_scale)
                new_h = int(img.height * final_scale)

                resized = img.resize((new_w, new_h),
                                     Image.Resampling.LANCZOS)

                photo = ImageTk.PhotoImage(resized)
                self.canvas.image = photo

                self.canvas.create_image(x, baseline,
                                         image=photo,
                                         anchor="sw")

                x += new_w + 15

    def draw_scene(self):
        self.canvas.delete("all")
        self.draw_lines()

        self.draw_word(self.min_scale)
        self.draw_word(self.max_scale)

        if self.show_black:
            self.draw_word(1.0)


if __name__ == "__main__":
    app = HandFontEditor()
    app.mainloop()