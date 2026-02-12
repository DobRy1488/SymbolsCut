import os

rus = list(
    "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЭЮЯ" +
    "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
)

eng = list(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ" +
    "abcdefghijklmnopqrstuvwxyz"
)

symbols = list(
    "0123456789" +
    ".,!?@#$%&()[]{}:;\"'<>/*-+="
)

category_map = {
    "russian": rus,
    "english": eng,
    "symbols": symbols
}

ROOT = "letters"

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


def apply_suffix_if_needed(category, char):
    if category in ("russian", "english") and char.islower():
        return char + "l"
    return char


def symbol_to_filename(char):
    if char.isdigit():
        return char
    return SYMBOL_NAME_MAP.get(char, f"u{ord(char):04X}")


def rename_in_category(category_name, symbols_list):
    category_path = os.path.join(ROOT, category_name)
    if not os.path.isdir(category_path):
        return

    for font_folder in os.listdir(category_path):
        font_path = os.path.join(category_path, font_folder)
        if not os.path.isdir(font_path):
            continue

        files = sorted(os.listdir(font_path))

        temp_map = []  # (temp_name, final_name)

        # ---------- PASS 1: во временные имена ----------
        for filename in files:
            name, ext = os.path.splitext(filename)
            if not name.isdigit():
                continue

            index = int(name) - 1
            if index < 0 or index >= len(symbols_list):
                continue

            char = symbols_list[index]

            if category_name == "symbols":
                base = symbol_to_filename(char)
            else:
                base = apply_suffix_if_needed(category_name, char)

            temp_name = f"__tmp__{filename}"
            temp_map.append((temp_name, f"{base}{ext}"))

            os.rename(
                os.path.join(font_path, filename),
                os.path.join(font_path, temp_name)
            )

        # ---------- PASS 2: во финальные имена ----------
        counters = {}

        for temp_name, final_name in temp_map:
            base, ext = os.path.splitext(final_name)

            counters.setdefault(base, 0)
            counters[base] += 1

            if counters[base] == 1:
                out_name = final_name
            else:
                out_name = f"{base}_{counters[base]:02d}{ext}"

            os.rename(
                os.path.join(font_path, temp_name),
                os.path.join(font_path, out_name)
            )

            print(f"{temp_name} → {out_name}")


def main():
    for category, symbols_list in category_map.items():
        print(f"\n=== Обрабатываю: {category} ===")
        rename_in_category(category, symbols_list)


if __name__ == "__main__":
    main()
