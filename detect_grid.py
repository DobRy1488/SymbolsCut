#!/usr/bin/env python3
"""
detect_grid.py — поиск сетки на отсканированном листе.

Результат сохраняется в:
  debug/<page>/original.png
  debug/<page>/masked.png
  debug/<page>/grid_lines.png
  debug/<page>/segments.png
  debug/<page>/cells.png
  debug/<page>/cells.json   ← JSON с координатами клеток + категория + формат
"""

import os
import math
import cv2
import json
import numpy as np
from PIL import Image
import tkinter as tk
from tkinter import filedialog


# ============================================================
# НАСТРОЙКИ
# ============================================================
DEBUG_ROOT = "debug"

ASSUME_DPI = 300
MIN_LINE_LEN_CM = 6.0          # минимальная длина линии
GRID_DILATE = 2
EDGE_CROP_RATIO = 0.02
SEGMENT_THR_RATIO = 0.25
MIN_SEGMENT_WIDTH_PX = 2


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================
def ensure_dir(p):
    os.makedirs(p, exist_ok=True)

def save_png(path, array_bgr):
    ensure_dir(os.path.dirname(path))
    Image.fromarray(cv2.cvtColor(array_bgr, cv2.COLOR_BGR2RGB)).save(path)

def save_gray_png(path, arr_gray):
    ensure_dir(os.path.dirname(path))
    Image.fromarray(arr_gray).save(path)

def load_image_cv(path):
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        raise RuntimeError(f"Не удалось загрузить файл: {path}")
    return img


def filter_grid_lines(mask, min_len_px):
    """Удаляет короткие линии, не являющиеся сеткой."""
    out = np.zeros_like(mask)
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for c in cnts:
        x, y, w, h = cv2.boundingRect(c)
        if w >= min_len_px or h >= min_len_px:
            cv2.drawContours(out, [c], -1, 255, -1)

    return out


def find_segments(mask, axis=0, thr_ratio=SEGMENT_THR_RATIO, min_w=MIN_SEGMENT_WIDTH_PX):
    """Поиск вертикальных/горизонтальных линий по сумме проекций."""
    proj = np.sum(mask > 0, axis=axis)
    if proj.max() == 0:
        return []

    thr = proj.max() * thr_ratio
    segs = []
    inside = False
    start = 0

    for i, v in enumerate(proj):
        if v > thr:
            if not inside:
                inside = True
                start = i
        else:
            if inside:
                end = i - 1
                if end - start + 1 >= min_w:
                    segs.append((start, end))
                inside = False

    if inside:
        end = len(proj) - 1
        if end - start + 1 >= min_w:
            segs.append((start, end))

    return segs


def estimate_angle(mask):
    """Оценка наклона сетки через Hough."""
    edges = cv2.Canny(mask, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 80,
                            minLineLength=100, maxLineGap=25)

    if lines is None:
        return 0.0

    angles = []
    for x1, y1, x2, y2 in lines[:, 0]:
        deg = math.degrees(math.atan2(y2 - y1, x2 - x1))
        angles.append(deg)

    if not angles:
        return 0.0

    med = float(np.median(angles))
    if med > 45:  med -= 90
    if med < -45: med += 90

    return med


def mask_crop_border(mask, crop_ratio=EDGE_CROP_RATIO):
    """Обнуляет края маски, чтобы игнорировать границы."""
    h, w = mask.shape[:2]
    cx = int(w * crop_ratio)
    cy = int(h * crop_ratio)

    m = mask.copy()
    m[:cy, :] = 0
    m[h-cy:, :] = 0
    m[:, :cx] = 0
    m[:, w-cx:] = 0
    return m


# ============================================================
# ФУНКЦИЯ ЗАПРОСА КАТЕГОРИИ И ФОРМАТА
# ============================================================
def ask_user_options():
    print("Выберите категорию:")
    categories = ["russian", "english", "symbols"]
    for i, c in enumerate(categories, 1):
        print(f"{i}. {c}")

    while True:
        try:
            c = int(input("Введите номер категории: "))
            if 1 <= c <= len(categories):
                category = categories[c-1]
                break
        except:
            pass
        print("Некорректный ввод, попробуйте ещё раз.")

    print("\nВыберите формат:")
    formats = ["1-11", "2-6", "3-4"]
    for i, f in enumerate(formats, 1):
        print(f"{i}. {f}")

    while True:
        try:
            f = int(input("Введите номер формата: "))
            if 1 <= f <= len(formats):
                format_value = formats[f-1]
                break
        except:
            pass
        print("Некорректный ввод, попробуйте ещё раз.")

    return category, format_value


# ============================================================
# ОСНОВНАЯ ЛОГИКА
# ============================================================
def process_image(path, category, format_value):
    base = os.path.splitext(os.path.basename(path))[0]
    out_dir = os.path.join(DEBUG_ROOT, base)
    ensure_dir(out_dir)

    print(f"\n=== Обрабатываю изображение: {path} ===")

    # 1) загрузка
    img = load_image_cv(path)
    H, W = img.shape[:2]

    save_png(os.path.join(out_dir, "original.png"), img)

    # 2) преобразование
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    inv = cv2.bitwise_not(gray)

    # 3) морфология
    kh = max(25, W // 120)
    kv = max(25, H // 120)
    kern_h = cv2.getStructuringElement(cv2.MORPH_RECT, (kh, 1))
    kern_v = cv2.getStructuringElement(cv2.MORPH_RECT, (1, kv))

    horiz = cv2.morphologyEx(inv, cv2.MORPH_OPEN, kern_h)
    vert  = cv2.morphologyEx(inv, cv2.MORPH_OPEN, kern_v)

    min_len_px = int((MIN_LINE_LEN_CM * ASSUME_DPI) / 2.54)

    horiz_f = filter_grid_lines(horiz, min_len_px)
    vert_f  = filter_grid_lines(vert,  min_len_px)

    grid = cv2.bitwise_or(horiz_f, vert_f)

    if GRID_DILATE > 0:
        grid = cv2.dilate(grid, np.ones((3,3), np.uint8),
                          iterations=GRID_DILATE)

    save_gray_png(os.path.join(out_dir, "masked.png"), grid)
    save_png(
        os.path.join(out_dir, "grid_lines.png"),
        cv2.addWeighted(img, 0.6,
                        cv2.cvtColor(grid, cv2.COLOR_GRAY2BGR),
                        0.4, 0)
    )

    # 4) удаляем края
    grid_cropped = mask_crop_border(grid)

    # 5) угол
    angle = estimate_angle(grid_cropped)
    print(f"[{base}] Угол наклона: {angle:.2f}°")

    # 6) поворот
    M = cv2.getRotationMatrix2D((W // 2, H // 2), angle, 1.0)
    grid_rot = cv2.warpAffine(grid, M, (W, H),
                              flags=cv2.INTER_NEAREST,
                              borderValue=0)
    img_rot  = cv2.warpAffine(img, M, (W, H),
                              flags=cv2.INTER_LINEAR,
                              borderValue=(255,255,255))

    # 7) повторная обработка
    grid_rot_cropped = mask_crop_border(grid_rot)

    vert_segs  = find_segments(grid_rot_cropped, axis=0)
    horiz_segs = find_segments(grid_rot_cropped, axis=1)

    print(f"[{base}] Линий найдено: vert={len(vert_segs)}, horiz={len(horiz_segs)}")

    if len(vert_segs) < 2 or len(horiz_segs) < 2:
        print(f"[{base}] Недостаточно линий, пробую fallback...")

        min_len2 = max(5, min_len_px // 2)
        horiz2 = filter_grid_lines(horiz, min_len2)
        vert2  = filter_grid_lines(vert,  min_len2)

        grid2 = cv2.bitwise_or(horiz2, vert2)
        grid2 = cv2.dilate(grid2, np.ones((3,3), np.uint8),
                           iterations=GRID_DILATE)

        grid_rot = cv2.warpAffine(grid2, M, (W, H),
                                  flags=cv2.INTER_NEAREST,
                                  borderValue=0)

        grid_rot_cropped = mask_crop_border(grid_rot)

        vert_segs  = find_segments(grid_rot_cropped, axis=0)
        horiz_segs = find_segments(grid_rot_cropped, axis=1)

        print(f"[{base}] После fallback: vert={len(vert_segs)}, horiz={len(horiz_segs)}")

    # 9) клетки
    cells_vis = img_rot.copy()
    cells = []

    if len(vert_segs) >= 2 and len(horiz_segs) >= 2:

        vert_coords  = sorted([ (s+e)//2 for (s,e) in vert_segs ])
        horiz_coords = sorted([ (s+e)//2 for (s,e) in horiz_segs ])

        for yi in range(len(horiz_coords)-1):
            y0, y1 = horiz_coords[yi], horiz_coords[yi+1]

            for xi in range(len(vert_coords)-1):
                x0, x1 = vert_coords[xi], vert_coords[xi+1]

                if (x1 - x0) < 4 or (y1 - y0) < 4:
                    continue

                cells.append((x0, y0, x1, y1))
                cv2.rectangle(cells_vis, (x0, y0), (x1, y1),
                              (255, 0, 0), 2)

    save_png(os.path.join(out_dir, "cells.png"), cells_vis)

    # ======================================================
    # 10) СОХРАНЯЕМ JSON (с категорией и форматом)
    # ======================================================
    json_path = os.path.join(out_dir, "cells.json")

    data = {
        "image_path": os.path.abspath(path),
        "image_name": os.path.basename(path),
        "debug_dir": out_dir,

        "width": W,
        "height": H,

        "angle": angle,
        "vert_lines":  [ (s+e)//2 for (s,e) in vert_segs ],
        "horiz_lines": [ (s+e)//2 for (s,e) in horiz_segs ],

        "cells": cells,

        # Новые поля:
        "category": category,
        "format": format_value
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    print(f"[{base}] JSON сохранён → {json_path}")

    return data


# ============================================================
# MAIN
# ============================================================
def main():
    root = tk.Tk()
    root.withdraw()

    # 1) спрашиваем параметры
    category, format_value = ask_user_options()

    # 2) выбор файлов
    files = filedialog.askopenfilenames(
        title="Выберите изображения",
        filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp *.tif *.tiff")]
    )

    if not files:
        print("Файлы не выбраны.")
        return

    ensure_dir(DEBUG_ROOT)

    # 3) обработка
    for f in files:
        try:
            process_image(f, category, format_value)
        except Exception as e:
            print(f"Ошибка при обработке {f}: {e}")


if __name__ == "__main__":
    main()
