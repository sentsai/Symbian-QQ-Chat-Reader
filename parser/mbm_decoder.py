import struct
from io import BytesIO
from PIL import Image


def decode_mbm(file_path: str) -> bytes:
    with open(file_path, 'rb') as f:
        data = f.read()

    if len(data) < 52:
        return _placeholder(40, 40)

    w = struct.unpack('<I', data[24:28])[0]
    h = struct.unpack('<I', data[28:32])[0]
    bpp = struct.unpack('<I', data[44:48])[0]

    if w <= 0 or h <= 0 or w > 4096 or h > 4096:
        w, h = 40, 40

    pixel_offset = 68

    if bpp == 24:
        result = _try_decode_mbm(data, pixel_offset, w, h)
        if result:
            return _save_png(result, w, h)

    return _placeholder(w, h)


def _save_png(result: list, w: int, h: int) -> bytes:
    img = Image.new('RGB', (w, h))
    pixels = img.load()
    for y in range(h):
        for x in range(w):
            idx = y * w + x
            if idx < len(result):
                pixels[x, y] = result[idx]
    buf = BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


def _try_decode_mbm(data: bytes, offset: int, w: int, h: int) -> list | None:
    pixel_count = w * h
    pixel_data = data[offset:offset + pixel_count * 3]
    if len(pixel_data) < pixel_count * 3:
        return None

    best_result = None
    best_unique = 0

    orders = [
        ('bgr_bottomup', lambda b, g, r, y, x: ((h - 1 - y) * w + x, (r, g, b))),
        ('bgr_topdown', lambda b, g, r, y, x: (y * w + x, (r, g, b))),
        ('rgb_bottomup', lambda b, g, r, y, x: ((h - 1 - y) * w + x, (b, g, r))),
        ('rgb_topdown', lambda b, g, r, y, x: (y * w + x, (b, g, r))),
        ('gbr_bottomup', lambda b, g, r, y, x: ((h - 1 - y) * w + x, (g, b, r))),
        ('gbr_topdown', lambda b, g, r, y, x: (y * w + x, (g, b, r))),
    ]

    for name, fn in orders:
        result = [(0, 0, 0)] * pixel_count
        valid = True
        for y in range(h):
            for x in range(w):
                idx = (y * w + x) * 3
                if idx + 2 >= len(pixel_data):
                    valid = False
                    break
                b_val = pixel_data[idx]
                g_val = pixel_data[idx + 1]
                r_val = pixel_data[idx + 2]
                try:
                    pos, color = fn(b_val, g_val, r_val, y, x)
                    if 0 <= pos < pixel_count:
                        result[pos] = color
                except Exception:
                    valid = False
                    break
            if not valid:
                break

        if valid:
            unique = len(set(result))
            if unique > best_unique:
                best_unique = unique
                best_result = result

    if best_result and best_unique >= 10:
        return best_result

    return None


def _placeholder(w: int, h: int) -> bytes:
    img = Image.new('RGB', (w, h), (220, 220, 220))
    buf = BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


def get_mbm_dimensions(file_path: str) -> tuple[int, int]:
    with open(file_path, 'rb') as f:
        data = f.read(48)
    if len(data) < 48:
        return (40, 40)
    w = struct.unpack('<I', data[24:28])[0]
    h = struct.unpack('<I', data[28:32])[0]
    if w <= 0 or w > 4096 or h <= 0 or h > 4096:
        return (40, 40)
    return (w, h)