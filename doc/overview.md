# QQ Chat History Reader

## Intro
QQ Chat History Reader is a light-weight tool used to read QQ chat history from Symbian-version QQ clients. 

## How to use
1. Run main.py, app will prompt a web-view window. 
2. In the web-view window, click "Open Chat History" button to open the chat history file.
3. Chat history will be displayed in the web-view window.
4. User can select different themes, including classic Symbian QQ theme, or modern QQ theme, modern WeChat theme.

## Roadmap
1.0 MVP
- [x] Support Symbian-version QQ chat history files.
- [x] Display chat history in web-view window.
- [x] Support multiple themes, including classic Symbian QQ theme, or modern QQ theme, modern WeChat theme.

1.1 Refinement
- Support displaying avatar images.
    Avatar images are stored under each conversation folder (and the account root folder for self-avatar).
    File naming convention: `{qq_number}_{unix_timestamp}.png` or `{qq_number}_{unix_timestamp}.png.m`.
    The timestamp indicates when the avatar was updated; a contact may have multiple avatar files from different times.
    
    Two image formats exist:
    - `.png`: Actually Windows BMP format (not PNG), identifiable by the `BM` signature at offset 0.
      Typical specs: 40×40 px, 24-bit color, bottom-to-top row order, BGR pixel layout.
    - `.png.m`: Symbian MBM (Multi-BitMap) format, the native Symbian OS bitmap format.
      Identifiable by UID1=0x10000037 and UID2=0x10000042 at offset 0.
      Header is 60 bytes; pixel data starts at offset 60, stored top-to-bottom (opposite of BMP).
      Supports 8bpp (with palette), 24bpp (BGR), and 32bpp (0x00BBGGRR) color depths.
    
    Requirements:
    - Decode `.png` (BMP) files using PIL with BM signature validation.
    - Decode `.png.m` (MBM) files with proper header parsing (60-byte header, UID validation),
      support for 8bpp/24bpp/32bpp color depths, and top-to-bottom row order.
    - Prefer `.png` (BMP) over `.png.m` when both exist for the same timestamp,
      since the BMP file is a derived/cleaned copy and more reliable.
    - When a contact has multiple avatar files, use the one with the latest timestamp.
    - Display avatars in both the conversation list and the chat history view.
    - Show a placeholder (colored background with QQ number initials) when no avatar file exists or decoding fails.
    - Serve decoded avatar images via a dedicated `/api/avatar/{account_qq}/{contact_qq}` endpoint as PNG format.
      This endpoint handles avatar selection logic (latest timestamp, prefer BMP) server-side.
    - Avatar display varies by theme:
      - Modern QQ / WeChat themes: avatar next to each message bubble (like WeChat chat layout).
        Self-avatar displayed next to sent messages; contact avatar next to received messages.
        Self-avatar also displayed in the sidebar header area.
      - Symbian QQ theme: avatar displayed at the top of the conversation, before the QQ number.
    - Native avatar size is 40×40px; scale via CSS to fit each theme's avatar slot size.
- Support custom chat history directory.
    Users can open a different chat history directory via a folder-picker dialog.
    The dialog is triggered by a button in the sidebar header area, using pywebview's native folder dialog API.
    After selecting a new directory, the app rescans and refreshes all data.


