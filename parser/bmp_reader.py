from io import BytesIO
from PIL import Image


def read_bmp(file_path: str) -> bytes | None:
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
