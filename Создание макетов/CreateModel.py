from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# === Регистрируем шрифт с кириллицей (Calibri) ===
pdfmetrics.registerFont(TTFont("Calibri", "calibri.ttf"))

# ---------------- ПАРАМЕТРЫ ----------------
CELL_SIZE = 15     # мм
MARGIN_X = 10      # мм
MARGIN_Y = 10      # мм
FONT_NAME = "Calibri"
# -------------------------------------------

mm = 72 / 25.4
cell_pt = CELL_SIZE * mm
margin_x_pt = MARGIN_X * mm
margin_y_pt = MARGIN_Y * mm

# Символы
rus = list("АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЭЮЯ" +
           "абвгдеёжзийклмнопрстуфхцчшщъыьэюя")
eng = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ" +
           "abcdefghijklmnopqrstuvwxyz")
digits = list("0123456789")
symbols = list(".,!?@#$%&()[]{}:;\"'<>/*-+=-")

# Конфигурации для групп:
# (название, список символов, экземпляров, колонок)
groups = [
    ("Русский алфавит", rus, 10, 1),
    ("Английский алфавит", eng, 5, 2),
    ("Цифры и символы", digits + symbols, 2, 3),
]

def draw_template(filename="letters_template.pdf"):
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4

    for _, symbols, copies, ncols in groups:
        x = margin_x_pt
        y = height - margin_y_pt - cell_pt
        col_count = 0

        for s in symbols:
            # эталон
            c.setStrokeColor(colors.cyan)
            c.rect(x, y, cell_pt, cell_pt)
            c.setFillColor(colors.cyan)
            c.setFont(FONT_NAME, cell_pt * 0.6)
            c.drawCentredString(x + cell_pt/2, y + cell_pt*0.2, s)

            # пустые клетки справа
            for i in range(1, copies + 1):
                c.setStrokeColor(colors.cyan)
                c.rect(x + i*cell_pt, y, cell_pt, cell_pt)

            # переход к следующей строке
            y -= cell_pt

            # если вышли за страницу по высоте
            if y < margin_y_pt:
                col_count += 1
                if col_count < ncols:
                    # новая колонка (без отступа)
                    x += (copies + 1) * cell_pt
                    y = height - margin_y_pt - cell_pt
                else:
                    # новая страница
                    c.showPage()
                    x = margin_x_pt
                    y = height - margin_y_pt - cell_pt
                    col_count = 0

        c.showPage()

    c.save()
    print(f"Макет сохранён: {filename}")

draw_template("letters_template.pdf")
