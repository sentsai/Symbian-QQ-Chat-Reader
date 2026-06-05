import sys
import os
import struct
from io import BytesIO
from PIL import Image


def _decompress_rle(data: bytes, expected_size: int) -> bytearray | None:
    try:
        pos = 0
        output = bytearray()
        while pos < len(data) and len(output) < expected_size:
            b = data[pos]
            pos += 1
            if b & 0x80:
                count = (b & 0x7F) + 1
                if pos >= len(data):
                    return None
                val = data[pos]
                pos += 1
                output.extend([val] * count)
            else:
                count = b + 1
                end = min(pos + count, len(data))
                output.extend(data[pos:end])
                pos = end
        if len(output) < expected_size:
            return None
        return output[:expected_size]
    except Exception:
        return None


def decode_mbm(file_path: str) -> bytes | None:
    try:
        with open(file_path, 'rb') as f:
            data = f.read()

        if len(data) < 60:
            return None

        uid1 = struct.unpack_from('<I', data, 0)[0]
        uid2 = struct.unpack_from('<I', data, 4)[0]
        if uid1 != 0x10000037 or uid2 != 0x10000042:
            return None

        w = struct.unpack_from('<I', data, 24)[0]
        h = struct.unpack_from('<I', data, 28)[0]
        bpp = struct.unpack_from('<I', data, 44)[0]
        palette_count = struct.unpack_from('<I', data, 52)[0]
        compression = struct.unpack_from('<I', data, 56)[0]

        if w <= 0 or h <= 0 or w > 4096 or h > 4096:
            return None

        offset = 60
        img = Image.new('RGB', (w, h))
        pixels = img.load()

        if bpp == 8:
            if compression == 0:
                palette_size = palette_count * 4
                palette_data = data[offset:offset + palette_size]
                if palette_count > 0 and len(palette_data) < palette_size:
                    return None
                palette = []
                for i in range(palette_count):
                    b_val = palette_data[i * 4]
                    g_val = palette_data[i * 4 + 1]
                    r_val = palette_data[i * 4 + 2]
                    palette.append((r_val, g_val, b_val))
                pixel_offset = offset + palette_size
                pixel_data = data[pixel_offset:pixel_offset + w * h]
                if len(pixel_data) < w * h:
                    return None
                for y in range(h):
                    for x in range(w):
                        idx = pixel_data[y * w + x]
                        if idx < len(palette):
                            pixels[x, y] = palette[idx]
            elif compression == 1:
                compressed = data[offset:]
                raw = _decompress_rle(compressed, w * h)
                if raw is None:
                    return None
                for y in range(h):
                    for x in range(w):
                        idx = raw[y * w + x]
                        gray = idx
                        pixels[x, y] = (gray, gray, gray)
            else:
                return None

        elif bpp == 24:
            needed = w * h * 3
            if compression == 0:
                pixel_data = data[offset:offset + needed]
                if len(pixel_data) < needed:
                    return None
            elif compression == 4:
                compressed = data[offset:]
                raw = _decompress_rle(compressed, needed)
                if raw is None:
                    return None
                pixel_data = raw
            else:
                return None
            for y in range(h):
                for x in range(w):
                    i = (y * w + x) * 3
                    b_val = pixel_data[i]
                    g_val = pixel_data[i + 1]
                    r_val = pixel_data[i + 2]
                    pixels[x, y] = (r_val, g_val, b_val)

        elif bpp == 32:
            needed = w * h * 4
            if compression == 0:
                pixel_data = data[offset:offset + needed]
                if len(pixel_data) < needed:
                    return None
            elif compression == 5:
                compressed = data[offset:]
                raw = _decompress_rle(compressed, needed)
                if raw is None:
                    return None
                pixel_data = raw
            else:
                return None
            for y in range(h):
                for x in range(w):
                    i = (y * w + x) * 4
                    b_val = pixel_data[i]
                    g_val = pixel_data[i + 1]
                    r_val = pixel_data[i + 2]
                    pixels[x, y] = (r_val, g_val, b_val)

        else:
            return None

        buf = BytesIO()
        img.save(buf, format='PNG')
        return buf.getvalue()

    except Exception:
        return None


def decode_bmp(file_path: str) -> bytes | None:
    try:
        with open(file_path, 'rb') as f:
            data = f.read()

        if data[:2] != b'BM':
            return None

        img = Image.open(BytesIO(data))
        buf = BytesIO()
        img.save(buf, format='PNG')
        return buf.getvalue()
    except Exception:
        return None


def main():
    if len(sys.argv) < 2:
        print('Usage: python decode_avatar.py <file.png.m|file.png> [output.png]')
        print('')
        print('Decode Symbian QQ avatar files to standard PNG format.')
        print('')
        print('Supported formats:')
        print('  .png.m  - Symbian MBM (Multi-BitMap) format')
        print('           Supports uncompressed and RLE-compressed variants:')
        print('           8bpp (palette/grayscale), 24bpp (BGR), 32bpp (0x00BBGGRR)')
        print('  .png    - Windows BMP format (not actual PNG despite extension)')
        print('')
        print('Examples:')
        print('  python decode_avatar.py 75508799_1321682756.png.m')
        print('  python decode_avatar.py 1058762402_1310869444.png output.png')
        sys.exit(1)

    input_path = sys.argv[1]
    if not os.path.isfile(input_path):
        print(f'Error: File not found: {input_path}')
        sys.exit(1)

    if input_path.endswith('.png.m'):
        print(f'Decoding MBM file: {input_path}')
        png_data = decode_mbm(input_path)
        fmt = 'MBM'
    elif input_path.endswith('.png'):
        print(f'Decoding BMP file: {input_path}')
        png_data = decode_bmp(input_path)
        fmt = 'BMP'
    else:
        print(f'Error: Unsupported file extension. Use .png or .png.m files.')
        sys.exit(1)

    if png_data is None:
        print(f'Error: Failed to decode {fmt} file.')
        print(f'  The file may be corrupted or use an unsupported compression variant.')
        sys.exit(1)

    if len(sys.argv) >= 3:
        output_path = sys.argv[2]
    else:
        base = os.path.splitext(input_path)[0]
        if base.endswith('.png'):
            base = os.path.splitext(base)[0]
        output_path = base + '_decoded.png'

    with open(output_path, 'wb') as f:
        f.write(png_data)

    img = Image.open(BytesIO(png_data))
    print(f'Success! Decoded {fmt} -> PNG')
    print(f'  Size: {img.size[0]}x{img.size[1]} px')
    print(f'  Mode: {img.mode}')
    print(f'  Output: {output_path}')


if __name__ == '__main__':
    main()
