from io import BytesIO
from PIL import Image


def read_bmp(file_path: str) -> bytes:
    with open(file_path, 'rb') as f:
        data = f.read()

    if data[:2] != b'BM':
        return _read_fallback(file_path, data)

    img = Image.open(BytesIO(data))
    buf = BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


def _read_fallback(file_path: str, data: bytes) -> bytes:
    img = Image.open(BytesIO(data))
    buf = BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()