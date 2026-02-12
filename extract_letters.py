#!/usr/bin/env python3
import os
import cv2
import json
import numpy as np
from PIL import Image
import tkinter as tk
from tkinter import filedialog

# =====================================================
# SETTINGS
# =====================================================

TARGET_SIZE = 400   # больше НЕ используется, оставлено для совместимости
MIN_PIXELS_IN_CELL = 50
PAD_BBOX = 4

# =====================================================
# HELPERS
# =====================================================

def ensure_dir(p):
    os.makedirs(p, exist_ok=True)

def save_rgba(path, arr):
    ensure_dir(os.path.dirname(path))
    Image.fromarray(arr).save(path)

def clean_grid_inside(cell, grid_mask=None):
    if grid_mask is None:
        return cell
    result = cell.copy()
    result[grid_mask > 0] = 255
    return result

def extract_alpha_mask(cell):
    blur = cv2.GaussianBlur(cell, (5, 5), 0)
    _, mask = cv2.threshold(
        blur, 0, 255,
        cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )

    cnts, hier = cv2.findContours(
        mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE
    )
    alpha = np.zeros_like(mask)

    if hier is not None:
        for i, c in enumerate(cnts):
            if cv2.contourArea(c) < 20:
                continue

            is_hole = hier[0][i][3] != -1
            color = 0 if is_hole else 255
            cv2.drawContours(alpha, [c], -1, color, -1)

    return alpha

# =====================================================
# ✨ ИЗМЕНЕНА ТОЛЬКО ЭТА ФУНКЦИЯ ✨
# =====================================================

def cut_and_resize(cell, alpha):
    pts = cv2.findNonZero(alpha)
    if pts is None:
        return None

    bx, by, bw, bh = cv2.boundingRect(pts)

    bx0 = max(0, bx - PAD_BBOX)
    by0 = max(0, by - PAD_BBOX)
    bx1 = min(alpha.shape[1], bx + bw + PAD_BBOX)
    by1 = min(alpha.shape[0], by + bh + PAD_BBOX)

    cut = cell[by0:by1, bx0:bx1]
    a = alpha[by0:by1, bx0:bx1]

    if cut.size == 0:
        return None

    # GRAY → RGBA, БЕЗ масштабирования
    rgb = cv2.cvtColor(cut, cv2.COLOR_GRAY2BGR)
    rgba = cv2.cvtColor(rgb, cv2.COLOR_BGR2BGRA)
    rgba[:, :, 3] = a

    return rgba

# =====================================================
# SYMBOL EXTRACTOR
# =====================================================

class SymbolExtractor:
    def __init__(self):
        # global next number per category
        self.next_index = {}  # category -> int

    def _get_next_base(self, category):
        if category not in self.next_index:
            self.next_index[category] = 1
        return self.next_index[category]

    def _advance_base(self, category, delta):
        if category not in self.next_index:
            self.next_index[category] = 1
        self.next_index[category] += delta

    def process_page(self, json_path):
        print(f"[+] Обработка JSON: {json_path}")

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        page_img_path = data.get("image_path")
        if not page_img_path or not os.path.exists(page_img_path):
            print("[-] Не найдено изображение:", page_img_path)
            return

        img = cv2.imread(page_img_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            print("[-] Не удалось загрузить изображение:", page_img_path)
            return

        angle = data.get("angle", 0)
        if angle != 0:
            H, W = img.shape
            M = cv2.getRotationMatrix2D((W // 2, H // 2), angle, 1.0)
            img = cv2.warpAffine(img, M, (W, H), borderValue=255)

        cells = data.get("cells", [])
        category = data.get("category", "symbols")
        fmt = data.get("format", "1-11")

        try:
            columns, per_col = map(int, fmt.split("-"))
        except Exception as e:
            print("[-] Неправильный формат в JSON:", fmt, e)
            return

        fonts_per_block = per_col - 1
        if fonts_per_block <= 0:
            print("[-] per_col должен быть >= 2.")
            return

        # -------- группировка по строкам --------

        rows = []
        for c in cells:
            x0, y0, x1, y1 = c
            center = (y0 + y1) // 2
            rows.append((center, c))
        rows.sort(key=lambda x: x[0])

        heights = [abs(c[3] - c[1]) for _, c in rows] if rows else [0]
        avg_h = int(np.median(heights)) if heights else 0
        thr = max(10, avg_h // 2) if avg_h > 0 else 20

        rows_grouped = []
        current = []
        last = None

        for cy, c in rows:
            if last is None or abs(cy - last) < thr:
                current.append(c)
            else:
                rows_grouped.append(current)
                current = [c]
            last = cy
        if current:
            rows_grouped.append(current)

        if not rows_grouped:
            print("[-] Не найдены строки.")
            return

        for i in range(len(rows_grouped)):
            rows_grouped[i] = sorted(rows_grouped[i], key=lambda c: c[0])

        rows_count = len(rows_grouped)
        base_number = self._get_next_base(category)

        # -------- основной обход --------

        for col in range(columns):
            for r in range(rows_count):
                row_cells = rows_grouped[r]
                block_start = col * per_col

                for j in range(1, per_col):
                    idx_in_row = block_start + j
                    if idx_in_row < 0 or idx_in_row >= len(row_cells):
                        continue

                    x0, y0, x1, y1 = row_cells[idx_in_row]
                    raw = img[y0:y1, x0:x1]

                    alpha = extract_alpha_mask(raw)
                    if cv2.countNonZero(alpha) < MIN_PIXELS_IN_CELL:
                        continue

                    result = cut_and_resize(raw, alpha)
                    if result is None:
                        continue

                    out_dir = os.path.join(
                        "letters", category, f"font{j}"
                    )
                    ensure_dir(out_dir)

                    number = base_number + col * rows_count + r
                    out_path = os.path.join(out_dir, f"{number}.png")
                    save_rgba(out_path, result)

        self._advance_base(category, columns * rows_count)
        print("[+] Готово.")

# =====================================================
# RUNNER
# =====================================================

def main():
    root = tk.Tk()
    root.withdraw()

    files = filedialog.askopenfilenames(
        title="Выберите JSON (cells.json)",
        filetypes=[("JSON", "*.json")]
    )
    if not files:
        print("Файлы не выбраны.")
        return

    extractor = SymbolExtractor()
    for f in files:
        extractor.process_page(f)

    print("\n=== Все страницы обработаны ===")

if __name__ == "__main__":
    main()
