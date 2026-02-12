import os
import random
import yaml
import re
from PIL import Image, ImageDraw
from tkinter import Tk, filedialog

# =====================================================
# СТРАНИЦА
# =====================================================

DPI = 1200

A4_WIDTH_CM = 21.0
A4_HEIGHT_CM = 29.7
MARGIN_CM = 1.0
LINE_SPACING_CM = 1.0

LINE_COLOR = (60, 110, 190)
LINE_THICKNESS_MM = 0.3
BACKGROUND_COLOR = (255, 255, 255)

LETTERS_DIR = "letters"
OUTPUT_DIR = "output_pages"

# =====================================================
# СИМВОЛЫ
# =====================================================

SYMBOL_NAME_MAP = {
    ".": "dot", ",": "comma", "!": "excl", "?": "q",
    "+": "pl", "-": "min", "*": "mul", "/": "div", "=": "eq",
    "<": "lt", ">": "gt",
    "(": "lp", ")": "rp",
    "[": "lb", "]": "rb",
    "{": "lc", "}": "rc",
    "@": "at", "#": "hash", "$": "dol",
    "%": "pct", "&": "and",
    ":": "col", ";": "sc",
    "\"": "qt", "'": "ap",
}

# =====================================================
# ЕДИНИЦЫ
# =====================================================

def cm_to_px(cm):
    return int(cm * DPI / 2.54)

def mm_to_px(mm):
    return int(mm * DPI / 25.4)

PAGE_W = cm_to_px(A4_WIDTH_CM)
PAGE_H = cm_to_px(A4_HEIGHT_CM)
MARGIN_PX = cm_to_px(MARGIN_CM)
LINE_SPACING_PX = cm_to_px(LINE_SPACING_CM)
LINE_WIDTH_PX = mm_to_px(LINE_THICKNESS_MM)

MAX_LINES_PER_PAGE = (PAGE_H - 2 * MARGIN_PX) // LINE_SPACING_PX

# =====================================================
# ДИАПАЗОНЫ
# =====================================================

def parse_mm_range(value):
    if isinstance(value, list):
        return tuple(sorted(mm_to_px(v) for v in value))
    else:
        px = mm_to_px(value)
        return (-px, px)

def parse_float_range(value):
    if isinstance(value, list):
        return tuple(sorted(value))
    else:
        return (-value, value)

# =====================================================
# ФАЙЛЫ СТРАНИЦ
# =====================================================

def ensure_output_dir():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

def get_next_page_number():
    ensure_output_dir()
    existing = []
    for f in os.listdir(OUTPUT_DIR):
        match = re.match(r"page_(\d+)\.png", f)
        if match:
            existing.append(int(match.group(1)))
    return max(existing, default=0) + 1

def save_page(letters_layer, page_number):
    letters_path = os.path.join(OUTPUT_DIR, f"letters-page_{page_number}.png")
    bg_path = os.path.join(OUTPUT_DIR, f"full-page_{page_number}.png")

    letters_layer.save(letters_path, dpi=(DPI, DPI))

    bg = Image.new("RGB", (PAGE_W, PAGE_H), BACKGROUND_COLOR)
    draw = ImageDraw.Draw(bg)

    y = MARGIN_PX
    while y < PAGE_H - MARGIN_PX:
        draw.line(
            [(MARGIN_PX, y), (PAGE_W - MARGIN_PX, y)],
            fill=LINE_COLOR,
            width=LINE_WIDTH_PX
        )
        y += LINE_SPACING_PX

    bg.paste(letters_layer, (0, 0), letters_layer)
    bg.save(bg_path, dpi=(DPI, DPI))

    print(f"Сохранена страница {page_number}")

# =====================================================
# СТИЛЬ
# =====================================================

def load_style(path):
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    style = {}

    style["kerning_px"] = tuple(sorted(mm_to_px(x) for x in cfg["kerning_mm"]))
    style["space_px"] = tuple(sorted(mm_to_px(x) for x in cfg["space_mm"]))

    style["baseline_jitter_px"] = parse_mm_range(cfg["baseline_jitter_mm"])
    style["line_spacing_jitter_px"] = parse_mm_range(cfg["line_spacing_jitter_mm"])

    style["scale_jitter"] = parse_float_range(cfg["scale_jitter"])
    style["rotation_deg"] = parse_float_range(cfg["rotation_deg"])

    desc = cfg["descenders"]
    style["desc_letters"] = set(desc["letters"])
    style["desc_anchor_px"] = mm_to_px(desc["anchor_top_mm"])
    style["desc_anchor_jitter_px"] = tuple(
        sorted(mm_to_px(x) for x in desc["anchor_jitter_mm"])
    )

    punct = cfg["punctuation"]
    style["punct_letters"] = set(punct["letters"])
    style["punct_anchor_px"] = mm_to_px(punct["anchor_top_mm"])
    style["punct_anchor_jitter_px"] = tuple(
        sorted(mm_to_px(x) for x in punct["anchor_jitter_mm"])
    )

    overlaps_px = {}
    for ch, data in cfg.get("overlaps", {}).items():
        v = data.get("right_mm", 0)
        if isinstance(v, list):
            overlaps_px[ch] = tuple(sorted(mm_to_px(x) for x in v))
        else:
            px = mm_to_px(v)
            overlaps_px[ch] = (px, px)

    style["overlap_right_px"] = overlaps_px

    return style

# =====================================================
# БУКВЫ
# =====================================================

def scan_fonts(cat):
    base = os.path.join(LETTERS_DIR, cat)
    if not os.path.exists(base):
        return []
    return [os.path.join(base, d) for d in os.listdir(base)]

RUS = scan_fonts("russian")
ENG = scan_fonts("english")
SYM = scan_fonts("symbols")

def is_russian(c):
    return c.lower() in "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"

def load_letter(ch):
    if ch == " ":
        return None

    if ch.isalpha():
        fonts = RUS if is_russian(ch) else ENG
        name = ch if ch.isupper() else f"{ch}l"
    else:
        fonts = SYM
        name = SYMBOL_NAME_MAP.get(ch, ch)

    for f in random.sample(fonts, len(fonts)):
        p = os.path.join(f, f"{name}.png")
        if os.path.exists(p):
            return Image.open(p).convert("RGBA")

    return None

# =====================================================
# ИЗМЕРЕНИЕ СЛОВА
# =====================================================

def measure_word(word, style):
    width = 0
    for ch in word:
        img = load_letter(ch)
        if not img:
            continue

        scale = 1 + random.uniform(*style["scale_jitter"])
        w = int(img.width * scale)

        overlap = random.randint(*style["overlap_right_px"].get(ch, (0, 0)))
        kerning = random.randint(*style["kerning_px"])

        width += w - overlap + kerning

    return width

# =====================================================
# РЕНДЕР
# =====================================================

def render(text, style):
    ensure_output_dir()
    page_number = get_next_page_number()

    letters_layer = Image.new("RGBA", (PAGE_W, PAGE_H), (0, 0, 0, 0))

    cx = MARGIN_PX
    line = 0

    tokens = re.findall(r"\n| +|[^\s]+", text)

    for token in tokens:

        if token == "\n":
            line += 1
            cx = MARGIN_PX
        elif token.isspace():
            cx += random.randint(*style["space_px"])
            continue
        else:
            if cx + measure_word(token, style) > PAGE_W - MARGIN_PX:
                line += 1
                cx = MARGIN_PX

        if line >= MAX_LINES_PER_PAGE:
            save_page(letters_layer, page_number)
            page_number += 1
            letters_layer = Image.new("RGBA", (PAGE_W, PAGE_H), (0, 0, 0, 0))
            line = 0
            cx = MARGIN_PX

        for ch in token:
            img = load_letter(ch)
            if not img:
                continue

            scale = 1 + random.uniform(*style["scale_jitter"])
            img = img.resize(
                (int(img.width * scale), int(img.height * scale)),
                Image.BICUBIC
            )

            img = img.rotate(
                random.uniform(*style["rotation_deg"]),
                expand=True,
                resample=Image.BICUBIC
            )

            w, h = img.size
            overlap = random.randint(*style["overlap_right_px"].get(ch, (0, 0)))
            kerning = random.randint(*style["kerning_px"])
            advance = w - overlap + kerning

            baseline_y = (
                MARGIN_PX
                + line * LINE_SPACING_PX
                + random.randint(*style["baseline_jitter_px"])
                + random.randint(*style["line_spacing_jitter_px"])
            )

            if ch in style["desc_letters"]:
                py = baseline_y - style["desc_anchor_px"] + random.randint(
                    *style["desc_anchor_jitter_px"]
                )
            elif ch in style["punct_letters"]:
                py = baseline_y - style["punct_anchor_px"] + random.randint(
                    *style["punct_anchor_jitter_px"]
                )
            else:
                py = baseline_y - h

            letters_layer.paste(img, (cx, py), img)
            cx += advance

    save_page(letters_layer, page_number)
    print("Готово")

# =====================================================
# ЗАПУСК
# =====================================================

if __name__ == "__main__":
    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    cfg = filedialog.askopenfilename(filetypes=[("YAML", "*.yaml *.yml")])
    if not cfg:
        exit()

    style = load_style(cfg)

    print("Введите текст. /accept — начать")
    lines = []
    while True:
        l = input()
        if l.strip() == "/accept":
            print("Обработка...")
            break
        lines.append(l)

    render("\n".join(lines), style)