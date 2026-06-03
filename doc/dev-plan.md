# QQ Chat History Reader — MVP Development Plan

## 1. Project Overview

A lightweight desktop tool to read and display Symbian QQ chat history. Built with Python + pywebview, featuring a web-based UI with multiple theme support.

**Core Value**: Decode the proprietary Symbian QQ binary chat format and present it in a readable, nostalgic, and modern way.

---

## 2. Chat History File Format Analysis

### 2.1 Directory Structure

```
chat-history/
├── {SelfQQ}/                          # Account root (e.g. 75508799)
│   ├── {FriendQQ}/                    # Per-contact folder
│   │   ├── msg.info                   # Chat messages (binary)
│   │   ├── {FriendQQ}_{timestamp}.png # Chat image (Windows BMP format)
│   │   └── {FriendQQ}_{timestamp}.png.m # Chat image (Symbian MBM format)
│   ├── CFStamplist.info               # Custom emoji/stamp list ("CS" header)
│   ├── blacklist.info                 # Blacklist (empty in samples)
│   └── stangerlist.info               # Stranger list (empty in samples)
```

Two accounts in sample data:
- **75508799**: 31 conversations, ~276 KB total
- **805149028**: 64 conversations, ~1.8 MB total

### 2.2 msg.info Binary Format

The chat history is stored in a custom binary format, **not encrypted**, using UTF-16-LE for text encoding.

**Message structure (per message):**

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0 | 2 bytes | Marker | Start marker: `0xA8 ??` or `0xA9 ??` (random byte, consistent within a message) |
| 2 | 4 bytes | Timestamp | Big-endian Unix timestamp (seconds since epoch) |
| 6 | 6 bytes | Reserved | Always `0x00 0x00 0x00 0x00 0x00 0x00` |
| 12 | 1 byte | Flag | `0x00` = received, `0x80` = sent, `0x50` = auto-reply/system message |
| 13 | N bytes | Content | UTF-16-LE encoded text, variable length |
| 13+N | 2 bytes | End Marker | Same as start marker (e.g. `0xA8 ??`) |

**Key observations:**
- Content length is implicit — read until the end marker is found
- Content byte count is always even (UTF-16-LE uses 2 bytes per character)
- Timestamps are valid Unix timestamps (e.g. `0x4D95EED5` = 2011-04-01 23:27:17)
- The `0x50` flag appears for auto-reply messages (e.g. "您好，我现在有事不在")
- System messages from QQ number 10000 use the `0xA9` marker prefix
- Some messages contain embedded URLs and QQ promotional text

### 2.3 Image Formats

**`.png` files — Windows BMP format:**
- Standard BMP file header (starts with `BM`)
- Can be decoded directly with Python Pillow library
- Various sizes (2.6 KB to 4.8 KB in samples)

**`.png.m` files — Symbian MBM (Multi-BitMap) format:**
- Symbian proprietary bitmap container
- File store header:
  - UID1 = `0x10000037` (Symbian direct file store)
  - UID2 = `0x10000042` (MBM file type)
  - UID3 = `0x00000000`
  - Checksum: 4 bytes
- Bitmap info (after UIDs):
  - Stream offset / data length fields
  - Width (4 bytes, little-endian)
  - Height (4 bytes, little-endian)
  - Bits per pixel (4 bytes, e.g. 0x18 = 24-bit)
  - Bitmap count (4 bytes, typically 1)
- Pixel data may use RLE compression (12-bit RLE common for 24-bit images)
- All sample `.png.m` files are 4868 bytes, 40×40 pixels, 24-bit color
- Can be decoded using `bmconv` tool or custom Python parser

### 2.4 Other Files

- **CFStamplist.info**: Custom emoji list, starts with `CS` header (0x4353), 24 bytes in sample
- **blacklist.info**: Empty in sample data
- **stangerlist.info**: Empty in sample data

---

## 3. Architecture

```
┌─────────────────────────────────────────────────┐
│                  main.py                         │
│            (Entry point + pywebview)             │
├─────────────────────┬───────────────────────────┤
│   Backend (Python)  │   Frontend (HTML/CSS/JS)  │
├─────────────────────┼───────────────────────────┤
│  parser/            │  themes/                   │
│  ├─ msg_parser.py   │  ├─ symbian/  (classic)   │
│  ├─ mbm_decoder.py  │  ├─ modern_qq/            │
│  └─ bmp_reader.py   │  └─ wechat/               │
│                     │                            │
│  server.py          │  app.js                    │
│  (Flask/API routes) │  (UI logic + rendering)   │
│                     │                            │
│  models.py          │                            │
│  (data structures)  │                            │
└─────────────────────┴───────────────────────────┘
```

### 3.1 Module Responsibilities

| Module | Responsibility |
|--------|---------------|
| `main.py` | App entry point, pywebview window creation |
| `parser/msg_parser.py` | Parse `msg.info` binary format → structured messages |
| `parser/mbm_decoder.py` | Decode Symbian MBM `.png.m` → PNG bytes |
| `parser/bmp_reader.py` | Read `.png` (BMP) files → PNG bytes for web display |
| `server.py` | Flask local server, REST API for frontend |
| `models.py` | Data classes: Message, Contact, ChatSession |
| `themes/` | CSS + HTML templates for 3 themes |
| `app.js` | Frontend logic: contact list, chat view, theme switching |

---

## 4. Data Model

```python
@dataclass
class Message:
    timestamp: int          # Unix timestamp
    direction: str          # "sent" | "received" | "system"
    content: str            # Decoded UTF-16-LE text
    marker: bytes           # Original 2-byte marker (for debugging)

@dataclass
class Contact:
    qq_number: str          # Friend's QQ number
    messages: list[Message] # All messages with this contact
    image_files: list[str]  # Associated image file paths

@dataclass
class Account:
    qq_number: str          # Self QQ number
    contacts: list[Contact] # All contacts
    chat_dir: str           # Path to account directory
```

---

## 5. API Design

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/accounts` | GET | List all detected QQ accounts |
| `/api/accounts/{qq}/contacts` | GET | List contacts for an account |
| `/api/accounts/{qq}/contacts/{friend_qq}/messages` | GET | Get all messages in a conversation |
| `/api/images/{path:path}` | GET | Serve decoded image (BMP or MBM → PNG) |
| `/api/themes` | GET | List available themes |
| `/api/themes/{name}` | GET | Get theme CSS |

---

## 6. MVP Feature Scope

### Phase 1: Core Parser (Must Have)
- [ ] `msg.info` binary parser with full format support
- [ ] Handle all marker types (`0xA8`, `0xA9`)
- [ ] Handle all flag types (`0x00`, `0x80`, `0x50`)
- [ ] UTF-16-LE text decoding
- [ ] Timestamp conversion to human-readable format
- [ ] Directory scanner: auto-discover accounts and contacts

### Phase 2: Image Support (Must Have)
- [ ] BMP (`.png`) reader → serve as PNG via Pillow
- [ ] MBM (`.png.m`) decoder → parse Symbian MBM header → extract pixel data → convert to PNG
- [ ] Handle RLE-compressed MBM bitmaps
- [ ] Image embedding in chat messages (match by timestamp in filename)

### Phase 3: Web UI + pywebview (Must Have)
- [ ] Flask local server with REST API
- [ ] pywebview window creation
- [ ] Contact list sidebar (sorted by recent message)
- [ ] Chat message display area with scroll
- [ ] Message bubbles: sent (right-aligned) vs received (left-aligned)
- [ ] Timestamp display per message
- [ ] System/auto-reply messages with distinct styling
- [ ] Image display inline in chat

### Phase 4: Three Themes (Must Have for MVP)
- [ ] **Classic Symbian QQ theme**: Green header, simple bubbles, retro font, Symbian-style contact list
- [ ] **Modern QQ theme**: Blue/white color scheme, rounded bubbles, modern typography
- [ ] **Modern WeChat theme**: Green/white scheme, WeChat-style bubbles and layout
- [ ] Theme switcher in UI header/settings

### Phase 5: Polish (Nice to Have)
- [ ] Search within messages
- [ ] Export chat as TXT/HTML
- [ ] Date grouping in chat view
- [ ] Unread message count on contacts
- [ ] Custom emoji display (from CFStamplist.info)

---

## 7. Tech Stack & Dependencies

| Component | Technology | Package |
|-----------|-----------|---------|
| Desktop window | pywebview | `pywebview>=4.0` |
| HTTP server | Flask | `flask>=3.0` |
| BMP image handling | Pillow | `Pillow>=10.0` |
| Frontend | Vanilla HTML/CSS/JS | No framework (keep it light) |
| MBM decoding | Custom Python | No external dependency |

**Why no frontend framework?** The UI is simple enough (contact list + chat view) that vanilla JS with template literals is sufficient. Keeps the app lightweight and fast to load.

---

## 8. MBM Decoder Strategy

The Symbian MBM format is the most complex part. Two approaches:

**Approach A: Custom Python parser (Recommended for MVP)**
- Parse the MBM file store header (UIDs, stream offsets)
- Read bitmap info header (width, height, bpp, compression)
- Decode pixel data:
  - Uncompressed: read raw pixel bytes directly
  - RLE12 (12-bit RLE): implement run-length decoding
  - RLE16/RLE24: similar RLE variants
- Convert decoded pixels to PNG via Pillow
- All sample `.png.m` files are 40×40 24-bit, likely uncompressed or RLE12

**Approach B: Bundle `bmconv.exe` (Fallback)**
- Ship the Symbian `bmconv.exe` tool
- Call it via subprocess to extract BMP from MBM
- Then convert BMP → PNG via Pillow
- Downside: Windows-only, requires shipping a binary

**Recommendation**: Start with Approach A. The sample files are small (40×40) and likely use simple compression. If complex MBM variants are encountered, fall back to Approach B.

---

## 9. Project File Structure

```
qq-chat-reader/
├── main.py                  # Entry point
├── server.py                # Flask API server
├── models.py                # Data classes
├── parser/
│   ├── __init__.py
│   ├── msg_parser.py        # msg.info binary parser
│   ├── mbm_decoder.py       # Symbian MBM decoder
│   └── bmp_reader.py        # BMP reader
├── web/
│   ├── index.html           # Main page
│   ├── app.js               # Frontend logic
│   └── themes/
│       ├── symbian.css       # Classic Symbian QQ theme
│       ├── modern_qq.css     # Modern QQ theme
│       └── wechat.css        # Modern WeChat theme
├── chat-history/            # Sample data (gitignored)
├── doc/
│   ├── overview.md
│   └── dev-plan.md          # This file
├── requirements.txt
└── .gitignore
```

---

## 10. Development Order

1. **`parser/msg_parser.py`** — Build and test the binary parser against sample data first
2. **`models.py`** — Define data structures
3. **`parser/bmp_reader.py`** — Simple BMP → PNG conversion
4. **`parser/mbm_decoder.py`** — MBM format decoder (most complex, iterate as needed)
5. **`server.py`** — Flask API wrapping the parsers
6. **`web/index.html` + `web/app.js`** — Frontend UI with one theme first
7. **`web/themes/symbian.css`** — Classic Symbian QQ theme
8. **`web/themes/modern_qq.css`** — Modern QQ theme
9. **`web/themes/wechat.css`** — Modern WeChat theme
10. **`main.py`** — Wire everything together with pywebview
11. **Testing & edge cases** — Handle malformed files, encoding errors, etc.

---

## 11. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| MBM RLE compression variants not fully documented | Cannot decode some images | Test against all sample `.png.m` files; fall back to `bmconv.exe` if needed |
| Mixed QQ versions (2007/2008/2009) may have different msg.info formats | Parser fails on some files | Build parser to be format-agnostic: scan for markers rather than fixed offsets |
| UTF-16-LE content may contain non-text binary data (emoji codes) | Garbled text display | Strip non-printable characters; map known QQ emoji codes to Unicode emoji |
| Large chat files (235 KB for one conversation) | Slow parsing | Parse lazily; cache parsed results |
| pywebview compatibility across Windows versions | App won't launch | Test on target Windows versions; provide fallback browser mode |

---

## 12. Success Criteria (MVP)

- [ ] Can open and correctly display all 95 conversations across both accounts
- [ ] Sent/received/system messages are visually distinguishable
- [ ] Timestamps display correctly in local time
- [ ] BMP images display inline in chat
- [ ] MBM images display inline in chat
- [ ] All 3 themes render correctly and can be switched at runtime
- [ ] App launches as a single window via `python main.py`
