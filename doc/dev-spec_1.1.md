# Dev Spec: v1.1 Refinement (v2 — Revised after first failed implementation)

## Overview

This spec covers two features for the 1.1 release:
1. **Avatar image support** — decode and display Symbian QQ avatar images across all themes
2. **Custom chat history directory** — allow users to pick a different chat history folder at runtime

### Lessons from v1 Implementation Failure

The first implementation had three critical problems:

1. **Layout destroyed / window slow / bubbles misaligned**: The previous spec asked to "restructure message layout" for Modern QQ and WeChat themes by adding avatars next to each bubble. This broke the existing flex-column layout. The `msg` divs use `flex-direction: column` with `align-items: flex-start/flex-end`, and inserting avatar elements alongside the bubble required changing to `flex-direction: row`, which cascaded into broken alignment, missing labels, and misplaced timestamps. **The fix**: Do NOT change the message layout structure at all. Keep avatars only in the sidebar contact list and the chat header. No avatars next to individual message bubbles.

2. **Avatar images not decoded / all showed fallback**: The MBM decoder rewrite was correct in principle (offset 60, BGR, UID validation), but the `decode_mbm()` function changed its return type from `bytes` to `Optional[bytes]` (returning `None` on failure). The caller in `server.py`'s `/api/images/` endpoint was not updated to handle `None`, causing a 500 error on every avatar request. Also, the new `/api/avatar/` endpoint had a bug where `read_bmp()` also started returning `None` but the endpoint didn't handle it. **The fix**: `decode_mbm()` and `read_bmp()` must return `bytes | None`. All callers must check for `None` and return 404. The existing `/api/images/` endpoint must also be updated.

3. **Folder picker button caused error**: The previous spec said to call `_webview_window.create_file_dialog()` directly from the Flask route handler. This fails because pywebview's `create_file_dialog()` must be called from the pywebview thread, not from Flask's worker thread. Calling it from Flask raises an exception. **The fix**: Use `webview.windows[0].create_file_dialog()` with `webview.start()` callback pattern, or use a thread-safe approach via `webview.evaluate_js()` on the window, or — simplest — use Python's built-in `tkinter.filedialog.askdirectory()` which works from any thread and doesn't require pywebview's window object at all.

---

## Feature 1: Avatar Image Support

### 1.1 MBM Decoder Rewrite

**Current state**: `parser/mbm_decoder.py` has a wrong pixel offset (68 instead of 60), uses a brute-force approach trying 6 different byte orders, and only supports 24bpp.

**Target**: Full rewrite with correct format parsing.

#### MBM File Format Reference

Verified against actual files in `chat-history/`:

```
Offset  Size  Description
0       4     UID1 = 0x10000037 (Symbian Direct File Store)
4       4     UID2 = 0x10000042 (Symbian Multi-BitMap)
8       4     UID3 (typically 0x00000000)
12      4     Checksum
16      4     Data size (file size - 8)
20      4     Pixel data size
24      4     Width (pixels)
28      4     Height (pixels)
32      4     Width (twips, usually same as pixel width)
36      4     Reserved (0)
40      4     Reserved (0)
44      4     Bits per pixel (8, 24, or 32)
48      4     Color flag (1 = color)
52      4     Palette entry count (0 for 24/32bpp)
56      4     Compression type (0 = none)
60+           Pixel data (top-to-bottom row order)
```

Verified: offset 60 works correctly. File `75508799_1321682756.png.m` is 4868 bytes, 40×40 24bpp, pixel data at offset 60 = 4800 bytes (40×40×3), matches exactly.

#### Decoding Rules

| BPP | Pixel Layout | Notes |
|-----|-------------|-------|
| 8 | Palette-indexed | Palette data sits between header and pixel data. Each palette entry is 4 bytes: `0x00BBGGRR`. Pixel data is 1 byte per pixel (index into palette). |
| 24 | BGR | 3 bytes per pixel: Blue, Green, Red. Row order: top-to-bottom. |
| 32 | 0x00BBGGRR | 4 bytes per pixel. Alpha byte is unused (always 0x00). Row order: top-to-bottom. |

#### Implementation

Rewrite `parser/mbm_decoder.py`:

```python
import struct
from io import BytesIO
from PIL import Image


def decode_mbm(file_path: str) -> bytes | None:
    """
    Decode a Symbian MBM file to PNG bytes.
    Returns None on any error (caller handles fallback).
    """
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

        if w <= 0 or h <= 0 or w > 4096 or h > 4096:
            return None

        offset = 60
        img = Image.new('RGB', (w, h))
        pixels = img.load()

        if bpp == 8:
            palette_size = palette_count * 4
            palette_data = data[offset:offset + palette_size]
            if len(palette_data) < palette_size:
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

        elif bpp == 24:
            needed = w * h * 3
            pixel_data = data[offset:offset + needed]
            if len(pixel_data) < needed:
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
            pixel_data = data[offset:offset + needed]
            if len(pixel_data) < needed:
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


def get_mbm_dimensions(file_path: str) -> tuple[int, int]:
    try:
        with open(file_path, 'rb') as f:
            data = f.read(48)
        if len(data) < 48:
            return (40, 40)
        w = struct.unpack_from('<I', data, 24)[0]
        h = struct.unpack_from('<I', data, 28)[0]
        if w <= 0 or w > 4096 or h <= 0 or h > 4096:
            return (40, 40)
        return (w, h)
    except Exception:
        return (40, 40)
```

Key changes from current code:
- **Pixel offset**: 60 (not 68)
- **UID validation**: Check bytes 0-7 for `0x10000037` + `0x10000042`
- **Remove brute-force**: No more trying 6 different byte orders. MBM is always BGR top-to-bottom.
- **8bpp support**: Read palette entries, map pixel indices to RGB colors
- **32bpp support**: Skip the unused alpha byte per pixel
- **Return None on failure**: Let the caller decide on fallback behavior instead of returning a placeholder image
- **IMPORTANT**: The function signature changes from `-> bytes` to `-> bytes | None`. ALL callers must be updated to handle `None`.

### 1.2 BMP Reader Enhancement

**Current state**: `parser/bmp_reader.py` works correctly for valid BMP files but has a silent fallback that tries PIL on any file.

**Changes**:
- Validate `BM` signature before processing
- Return `None` on failure instead of trying PIL fallback (caller handles fallback)
- **IMPORTANT**: Return type changes from `-> bytes` to `-> bytes | None`. ALL callers must be updated.

```python
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
```

### 1.3 Avatar Resolution Logic

**New module**: `parser/avatar_resolver.py`

Responsible for finding the best avatar file for a given contact.

**CRITICAL**: Self-avatars live in the **account root directory**, NOT in a contact subdirectory. There is no `{account_qq}/` subdirectory for the account itself. For example, account `75508799` has self-avatar files at `chat-history/75508799/75508799_*.png[.m]`, but there is no `chat-history/75508799/75508799/` directory.

```python
import os


def resolve_avatar(chat_dir: str, account_qq: str, contact_qq: str) -> str | None:
    """
    Find the best avatar file path for a contact.

    Logic:
    1. Determine search directory:
       - For self-avatar (contact_qq == account_qq): search in account root dir
         (chat_dir itself, e.g. chat-history/75508799/)
       - For contact avatar: search in {chat_dir}/{contact_qq}/ dir
         (e.g. chat-history/75508799/1058762402/)
    2. List all files matching pattern {contact_qq}_*.png and {contact_qq}_*.png.m
    3. Parse timestamps from filenames: {contact_qq}_{timestamp}.png
       - .png.m files: strip the .m suffix to get timestamp
       - Example: "1058762402_1310869444.png.m" → timestamp = 1310869444
    4. Group by timestamp; for each timestamp, prefer .png over .png.m
    5. Return the file path with the latest timestamp
    6. Return None if no avatar files found
    """
    if contact_qq == account_qq:
        search_dir = chat_dir
    else:
        search_dir = os.path.join(chat_dir, contact_qq)

    if not os.path.isdir(search_dir):
        return None

    candidates = []
    prefix = contact_qq + '_'
    for f in os.listdir(search_dir):
        if not f.startswith(prefix):
            continue
        if f.endswith('.png.m'):
            ts_str = f[len(prefix):-6]  # strip prefix and .png.m
        elif f.endswith('.png'):
            ts_str = f[len(prefix):-4]  # strip prefix and .png
        else:
            continue
        try:
            ts = int(ts_str)
        except ValueError:
            continue
        candidates.append((ts, f))

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0], reverse=True)
    best_ts = candidates[0][0]

    # Prefer .png over .png.m for the same timestamp
    for ts, f in candidates:
        if ts == best_ts and f.endswith('.png') and not f.endswith('.png.m'):
            return os.path.join(search_dir, f)

    return os.path.join(search_dir, candidates[0][1])
```

### 1.4 API Endpoint

**New endpoint**: `GET /api/avatar/{account_qq}/{contact_qq}`

**CRITICAL**: Both `decode_mbm()` and `read_bmp()` now return `bytes | None`. You MUST check for `None` and return 404. Also update the existing `/api/images/` endpoint to handle `None` returns.

```python
from parser.avatar_resolver import resolve_avatar

@app.route('/api/avatar/<account_qq>/<contact_qq>')
def get_avatar(account_qq, contact_qq):
    file_path = resolve_avatar(CHAT_HISTORY_DIR, account_qq, contact_qq)
    if file_path is None:
        return jsonify({'error': 'No avatar found'}), 404

    try:
        if file_path.endswith('.png.m'):
            png_data = decode_mbm(file_path)
        else:
            png_data = read_bmp(file_path)

        if png_data is None:
            return jsonify({'error': 'Decode failed'}), 404

        return Response(png_data, mimetype='image/png')
    except Exception:
        return jsonify({'error': 'Decode error'}), 404
```

**Also update** the existing `/api/images/` endpoint to handle `None` returns from `decode_mbm()` and `read_bmp()`:

```python
@app.route('/api/images/<path:img_path>')
def get_image(img_path):
    full_path = os.path.join(CHAT_HISTORY_DIR, img_path)
    full_path = os.path.normpath(full_path)
    if not full_path.startswith(os.path.normpath(CHAT_HISTORY_DIR)):
        return jsonify({'error': 'Invalid path'}), 403
    if not os.path.isfile(full_path):
        return jsonify({'error': 'Not found'}), 404

    try:
        if img_path.endswith('.png.m'):
            png_data = decode_mbm(full_path)
        elif img_path.endswith('.png'):
            png_data = read_bmp(full_path)
        else:
            return jsonify({'error': 'Unsupported format'}), 400

        if png_data is None:
            return jsonify({'error': 'Decode failed'}), 404

        return Response(png_data, mimetype='image/png')
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

### 1.5 Data Model Changes

**File**: `models.py`

Add `account_qq` field to `Contact` so it can construct its avatar URL. This is set during `scan_account()`.

```python
@dataclass
class Contact:
    qq_number: str
    account_qq: str = ''
    messages: list[Message] = field(default_factory=list)
    image_files: list[str] = field(default_factory=list)

    @property
    def avatar_url(self) -> str:
        return f'/api/avatar/{self.account_qq}/{self.qq_number}'

    @property
    def last_message(self) -> Message | None:
        return self.messages[-1] if self.messages else None

    @property
    def message_count(self) -> int:
        return len(self.messages)
```

Update `scan_account()` in `parser/msg_parser.py` to pass `account_qq`:

```python
contact = Contact(
    qq_number=entry,
    account_qq=account_name,  # ADD THIS LINE
    messages=messages,
    image_files=image_files,
)
```

Add `avatar_url` to `_serialize_contact()` in `server.py`:

```python
def _serialize_contact(contact: Contact) -> dict:
    last_msg = contact.last_message
    return {
        'qq_number': contact.qq_number,
        'avatar_url': contact.avatar_url,  # ADD THIS LINE
        'message_count': contact.message_count,
        'image_files': [os.path.relpath(f, CHAT_HISTORY_DIR).replace('\\', '/') for f in contact.image_files],
        'last_message': _serialize_message(last_msg) if last_msg else None,
    }
```

### 1.6 Frontend Changes

**File**: `web/index.html`

#### ⚠️ CRITICAL RULE: DO NOT change the message layout structure

The current message layout uses `flex-direction: column` with `align-items: flex-start/flex-end`. This MUST NOT be changed. Do NOT add avatar images next to message bubbles. Avatars appear ONLY in:

1. **Sidebar contact list** — replace the text-based `.contact-avatar` div
2. **Chat header** — show the contact's avatar next to the QQ number

#### Contact List (all themes)

Replace the current text-based `.contact-avatar` div with an `<img>` + fallback pattern:

Find this exact code in `renderContactList()`:
```javascript
item.innerHTML = `
  <div class="contact-avatar">${c.qq_number.slice(-2)}</div>
  <div class="contact-info">
```

Replace with:
```javascript
item.innerHTML = `
  <img class="contact-avatar" src="${c.avatar_url}" onerror="this.onerror=null;this.style.display='none';this.nextElementSibling.style.display='flex';">
  <div class="contact-avatar-fallback" style="display:none;">${c.qq_number.slice(-2)}</div>
  <div class="contact-info">
```

**IMPORTANT**: The `onerror` handler must set `this.onerror=null` first to prevent infinite loops, then hide the `<img>` and show the fallback `<div>`.

#### Chat Header — Contact Avatar

Find this exact code in `selectContact()`:
```javascript
document.getElementById('chat-title').textContent = qq;
```

Replace with:
```javascript
const chatTitle = document.getElementById('chat-title');
chatTitle.innerHTML = `<img class="chat-header-avatar" src="/api/avatar/${currentAccount}/${qq}" onerror="this.style.display='none';"> <span>${qq}</span>`;
```

#### ⚠️ DO NOT add avatars next to individual message bubbles

The `renderMessages()` function must NOT be modified. No avatar elements should be added to the `.msg` divs. The current layout is:

```html
<div class="msg msg-sent">
  <div class="msg-label">Me</div>
  <div class="msg-bubble">...</div>
  <div class="msg-time">...</div>
</div>
```

This structure must remain exactly as-is. Changing it to include avatars alongside bubbles broke the layout in v1.

### 1.7 CSS Changes Per Theme

**CRITICAL**: Only ADD new CSS rules. Do NOT modify existing rules for `.msg`, `.msg-bubble`, `.msg-sent`, `.msg-received`, `.msg-system`, `.msg-label`, `.msg-time`, `.contact-item`, `.contact-info`, `.contact-name`, `.contact-preview`, `.contact-time`. These are all working correctly and must not be touched.

#### New CSS rules to ADD (not replace) in each theme file:

**All themes** — add these rules at the END of each CSS file:

```css
.contact-avatar {
    object-fit: cover;
    image-rendering: pixelated;
    image-rendering: -webkit-crisp-edges;
}

.contact-avatar-fallback {
    color: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}

.chat-header-avatar {
    image-rendering: pixelated;
    image-rendering: -webkit-crisp-edges;
    vertical-align: middle;
}
```

#### Theme-specific sizing (append to each theme file):

**symbian.css** — append:
```css
.contact-avatar {
    width: 36px;
    height: 36px;
    border-radius: 2px;
}

.contact-avatar-fallback {
    width: 36px;
    height: 36px;
    background: #5a8a5a;
    font-size: 12px;
    border-radius: 2px;
}

.chat-header-avatar {
    width: 40px;
    height: 40px;
    border-radius: 2px;
    margin-right: 8px;
}
```

**modern_qq.css** — append:
```css
.contact-avatar {
    width: 42px;
    height: 42px;
    border-radius: 50%;
}

.contact-avatar-fallback {
    width: 42px;
    height: 42px;
    background: linear-gradient(135deg, #12b7f5, #0d8ed9);
    font-size: 13px;
    border-radius: 50%;
}

.chat-header-avatar {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    margin-right: 8px;
}
```

**wechat.css** — append:
```css
.contact-avatar {
    width: 40px;
    height: 40px;
    border-radius: 4px;
}

.contact-avatar-fallback {
    width: 40px;
    height: 40px;
    background: #07c160;
    font-size: 12px;
    border-radius: 4px;
}

.chat-header-avatar {
    width: 36px;
    height: 36px;
    border-radius: 4px;
    margin-right: 8px;
}
```

**IMPORTANT**: The existing `.contact-avatar` CSS rules in each theme file define `background`, `display: flex`, `align-items`, `justify-content`, `font-size`, and `flex-shrink`. These were for the old `<div>` element. Since we're now using an `<img>` element, the `background`, `display: flex`, `align-items`, `justify-content` properties are irrelevant for `<img>` (they only apply to the fallback `<div>`). The new rules above override the `width`, `height`, and `border-radius` while adding `object-fit: cover`. The fallback div gets its own `.contact-avatar-fallback` class with the old styling.

You MUST delete the old `.contact-avatar` block from each CSS file and replace it with the new rules above. The old block looks like:

```css
/* OLD — DELETE THIS ENTIRE BLOCK from each theme */
.contact-avatar {
    width: 36px;       /* varies by theme */
    height: 36px;      /* varies by theme */
    background: #5a8a5a;  /* varies by theme */
    color: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    border-radius: 2px;   /* varies by theme */
    flex-shrink: 0;
}
```

Replace it with the theme-specific `.contact-avatar` + `.contact-avatar-fallback` + `.chat-header-avatar` blocks shown above.

---

## Feature 2: Custom Chat History Directory

### 2.1 UI Trigger

Add a folder icon button (📁) in the sidebar header, next to the theme and language buttons.

Find this exact code in `index.html`:
```html
<div id="sidebar-actions">
  <button id="btn-theme" title="切换主题 / Switch Theme">🎨</button>
  <button id="btn-lang" title="Switch Language">EN</button>
</div>
```

Add the folder button BEFORE the theme button:
```html
<div id="sidebar-actions">
  <button id="btn-open-dir" title="Open Chat History Folder">📁</button>
  <button id="btn-theme" title="切换主题 / Switch Theme">🎨</button>
  <button id="btn-lang" title="Switch Language">EN</button>
</div>
```

### 2.2 Backend Endpoint — Using tkinter (NOT pywebview)

**⚠️ CRITICAL**: The previous implementation used `webview.create_file_dialog()` from a Flask route handler. This FAILS because pywebview's dialog methods must be called from the pywebview event loop thread, not from Flask's worker thread. Calling from Flask raises a `WebViewException` or silently fails.

**Solution**: Use Python's built-in `tkinter.filedialog.askdirectory()` instead. This works from any thread, requires no pywebview window reference, and produces a native folder picker on all platforms.

```python
import tkinter as tk
from tkinter import filedialog

@app.route('/api/open-directory', methods=['POST'])
def open_directory():
    global CHAT_HISTORY_DIR

    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    selected = filedialog.askdirectory(
        title='Select Chat History Folder',
        initialdir=CHAT_HISTORY_DIR,
    )
    root.destroy()

    if not selected:
        return jsonify({'changed': False, 'reason': 'cancelled'})

    if not _is_valid_chat_dir(selected):
        return jsonify({'changed': False, 'reason': 'invalid'})

    CHAT_HISTORY_DIR = selected
    accounts = scan_all_accounts(CHAT_HISTORY_DIR)
    return jsonify({
        'changed': True,
        'accounts': [_serialize_account(a) for a in accounts],
    })


def _is_valid_chat_dir(path: str) -> bool:
    """Check that the directory contains at least one subdirectory with msg.info."""
    try:
        for entry in os.listdir(path):
            sub = os.path.join(path, entry)
            if os.path.isdir(sub) and os.path.isfile(os.path.join(sub, 'msg.info')):
                return True
    except OSError:
        pass
    return False
```

**IMPORTANT**: Do NOT use `webview.create_file_dialog()` or `webview.FOLDER_DIALOG`. Do NOT add a `_webview_window` reference. Do NOT modify `main.py`. The tkinter approach is self-contained in `server.py`.

### 2.3 Frontend Flow

Add this JavaScript to `index.html` after the `init()` function:

```javascript
document.getElementById('btn-open-dir').addEventListener('click', async () => {
  try {
    const res = await fetch('/api/open-directory', { method: 'POST' });
    const data = await res.json();
    if (data.changed) {
      currentAccount = null;
      currentContact = null;
      document.getElementById('chat-title').textContent = t('select_contact');
      document.getElementById('chat-messages').innerHTML = '';
      await loadAccountsFromData(data.accounts);
    } else if (data.reason === 'invalid') {
      alert(currentLang === 'zh'
        ? '所选文件夹不包含有效的聊天记录'
        : 'Selected folder does not contain valid chat history');
    }
  } catch (e) {
    console.error('Failed to open directory:', e);
  }
});
```

Add a helper function to load accounts from data (avoid re-fetching):

```javascript
async function loadAccountsFromData(accounts) {
  const sel = document.getElementById('account-select');
  sel.innerHTML = '';
  if (accounts.length === 0) {
    sel.innerHTML = `<option>${t('no_contacts')}</option>`;
    return;
  }
  accounts.forEach(acc => {
    const opt = document.createElement('option');
    opt.value = acc.qq_number;
    opt.textContent = `${acc.qq_number} (${t('contacts_fmt', {n: acc.contact_count})})`;
    sel.appendChild(opt);
  });
  selectAccount(accounts[0].qq_number);
}
```

### 2.4 No Changes to main.py

The previous spec required modifying `main.py` to expose the pywebview window reference. This is no longer needed since we're using tkinter for the folder dialog. **Do NOT modify `main.py`.**

---

## Implementation Order

1. **Rewrite `mbm_decoder.py`** — correct offset (60), UID validation, 8/24/32bpp, return `bytes | None`
2. **Enhance `bmp_reader.py`** — add BM validation, return `bytes | None`
3. **Update `/api/images/` endpoint** in `server.py` — handle `None` returns from both decoders
4. **Create `avatar_resolver.py`** — avatar file selection logic
5. **Add `/api/avatar/` endpoint** in `server.py` — serve avatars, handle `None` returns
6. **Update `models.py`** — add `account_qq` field and `avatar_url` property to Contact
7. **Update `parser/msg_parser.py`** — pass `account_qq` to Contact constructor
8. **Update `_serialize_contact()`** in `server.py` — include `avatar_url`
9. **Update frontend HTML** — avatar `<img>` in contact list and chat header ONLY (NOT in message bubbles)
10. **Update CSS per theme** — replace old `.contact-avatar` block, add new avatar rules
11. **Add `/api/open-directory` endpoint** in `server.py` — using tkinter, NOT pywebview
12. **Add folder button and JS** in `index.html` — wire up the open directory flow

---

## Files to Modify

| File | Change |
|------|--------|
| `parser/mbm_decoder.py` | Full rewrite: correct offset 60, UID validation, 8/24/32bpp, return `bytes \| None` |
| `parser/bmp_reader.py` | Add BM validation, return `bytes \| None` |
| `parser/avatar_resolver.py` | **New file**: avatar file selection logic |
| `parser/msg_parser.py` | Pass `account_qq` to Contact during scan |
| `models.py` | Add `account_qq` field and `avatar_url` property to Contact |
| `server.py` | Add `/api/avatar/` and `/api/open-directory` endpoints, update `/api/images/` for None returns, update serialization |
| `web/index.html` | Avatar `<img>` in contact list + chat header, folder picker button, onerror fallback. **DO NOT modify renderMessages()** |
| `web/themes/symbian.css` | Replace `.contact-avatar` block, add `.contact-avatar-fallback` and `.chat-header-avatar` |
| `web/themes/modern_qq.css` | Replace `.contact-avatar` block, add `.contact-avatar-fallback` and `.chat-header-avatar` |
| `web/themes/wechat.css` | Replace `.contact-avatar` block, add `.contact-avatar-fallback` and `.chat-header-avatar` |

### Files NOT to Modify

| File | Reason |
|------|--------|
| `main.py` | No changes needed — tkinter folder dialog doesn't need pywebview window reference |
| `parser/__init__.py` | No changes needed |

---

## Checklist for Implementation

Before considering the implementation complete, verify ALL of the following:

- [ ] `decode_mbm()` returns `None` on invalid files (not a placeholder image)
- [ ] `read_bmp()` returns `None` on non-BMP files (not trying PIL fallback)
- [ ] `/api/images/` endpoint handles `None` returns from both decoders (returns 404, not 500)
- [ ] `/api/avatar/` endpoint handles `None` returns from both decoders (returns 404, not 500)
- [ ] Self-avatars are found in account root dir (e.g. `chat-history/75508799/75508799_*.png`)
- [ ] Contact avatars are found in contact subdirs (e.g. `chat-history/75508799/1058762402/1058762402_*.png`)
- [ ] `.png` files are preferred over `.png.m` files for the same timestamp
- [ ] Contact list shows `<img>` with `onerror` fallback to initials div
- [ ] Chat header shows avatar next to QQ number
- [ ] Message bubbles layout is UNCHANGED — no avatars next to bubbles
- [ ] Folder picker uses `tkinter.filedialog.askdirectory()`, NOT `webview.create_file_dialog()`
- [ ] No changes to `main.py`
- [ ] No changes to `renderMessages()` function
- [ ] Existing `.contact-avatar` CSS blocks are replaced (not duplicated)
- [ ] All three theme CSS files are updated
