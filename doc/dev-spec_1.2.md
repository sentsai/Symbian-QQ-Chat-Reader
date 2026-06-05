# Dev Spec: v1.2 UX Improvements

## Overview

Four UX improvements for the 1.2 release:
1. **Loading indicators** — skeleton screens for contact list and chat messages; spinner overlay during theme switching
2. **Layout, spacing, and font polish** — improve readability across all three themes without disrupting existing front-end logic
3. **Theme name fix** — "Modern Qq" → "Modern QQ"
4. **Language switch label** — show current language: "中" when in CN mode, "EN" when in EN mode

---

## 1. Loading Indicators

### 1.1 Skeleton Screen for Contact List

When `selectAccount()` is called, the contact list area shows a skeleton placeholder until the API response arrives and `renderContactList()` replaces it.

**Implementation in `web/index.html`**:

Add a CSS class `.skeleton-contacts` that renders 6–8 placeholder rows mimicking the contact item layout (avatar circle + two text bars). Each row uses a CSS shimmer animation.

```css
.skeleton-contacts {
  padding: 0;
}

.skeleton-contact-row {
  display: flex;
  align-items: center;
  padding: 10px 14px;
  gap: 10px;
  border-bottom: 1px solid #f0f0f0;
}

.skeleton-circle {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  background: linear-gradient(90deg, #e8e8e8 25%, #f5f5f5 50%, #e8e8e8 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  flex-shrink: 0;
}

.skeleton-lines {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.skeleton-line {
  height: 12px;
  border-radius: 4px;
  background: linear-gradient(90deg, #e8e8e8 25%, #f5f5f5 50%, #e8e8e8 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

.skeleton-line.short {
  width: 60%;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
```

In `selectAccount()`, insert the skeleton HTML before the API call:

```javascript
async function selectAccount(qq) {
  currentAccount = qq;
  currentContact = null;
  document.getElementById('chat-title').textContent = t('select_contact');
  document.getElementById('chat-messages').innerHTML = '';

  // Show skeleton in contact list
  const list = document.getElementById('contact-list');
  list.innerHTML = '<div class="skeleton-contacts">' +
    Array.from({length: 7}, () =>
      '<div class="skeleton-contact-row">' +
        '<div class="skeleton-circle"></div>' +
        '<div class="skeleton-lines">' +
          '<div class="skeleton-line"></div>' +
          '<div class="skeleton-line short"></div>' +
        '</div>' +
      '</div>'
    ).join('') +
  '</div>';

  const contacts = await api(`/api/accounts/${qq}/contacts`);
  renderContactList(contacts);
}
```

**Theme overrides for skeleton colors** — append to each theme CSS file:

| Theme | Skeleton background gradient | Border |
|-------|----------------------------|--------|
| `symbian.css` | `linear-gradient(90deg, #c8dcc8 25%, #d8ecd8 50%, #c8dcc8 75%)` | `1px solid #c8dcc8` |
| `modern_qq.css` | `linear-gradient(90deg, #e8e8e8 25%, #f5f5f5 50%, #e8e8e8 75%)` | `1px solid #f0f0f0` |
| `wechat.css` | `linear-gradient(90deg, #3a3a3a 25%, #444 50%, #3a3a3a 75%)` | `1px solid #3a3a3a` |

For `wechat.css`, the skeleton circle should use `border-radius: 4px` (square with slight rounding) instead of `50%` to match WeChat's avatar style.

### 1.2 Skeleton Screen for Chat Messages

When `selectContact()` is called, the chat messages area shows a skeleton placeholder until the API response arrives and `renderMessages()` replaces it.

```css
.skeleton-messages {
  padding: 16px 20px;
}

.skeleton-msg {
  display: flex;
  flex-direction: column;
  margin-bottom: 16px;
}

.skeleton-msg.right {
  align-items: flex-end;
}

.skeleton-msg.left {
  align-items: flex-start;
}

.skeleton-bubble {
  height: 40px;
  width: 55%;
  border-radius: 12px;
  background: linear-gradient(90deg, #e8e8e8 25%, #f5f5f5 50%, #e8e8e8 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

.skeleton-bubble.small {
  height: 28px;
  width: 35%;
}

.skeleton-time {
  height: 8px;
  width: 50px;
  margin-top: 6px;
  border-radius: 4px;
  background: linear-gradient(90deg, #e8e8e8 25%, #f5f5f5 50%, #e8e8e8 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}
```

In `selectContact()`, insert skeleton before the API call:

```javascript
async function selectContact(qq) {
  currentContact = qq;
  const chatTitle = document.getElementById('chat-title');
  chatTitle.innerHTML = `<img class="chat-header-avatar" src="/api/avatar/${currentAccount}/${qq}" onerror="this.style.display='none';"> <span>${qq}</span>`;
  document.querySelectorAll('.contact-item').forEach(el => {
    el.classList.toggle('active', el.dataset.qq === qq);
  });

  // Show skeleton in chat area
  const container = document.getElementById('chat-messages');
  const sides = ['left', 'right'];
  container.innerHTML = '<div class="skeleton-messages">' +
    Array.from({length: 6}, (_, i) =>
      '<div class="skeleton-msg ' + sides[i % 2] + '">' +
        '<div class="skeleton-bubble' + (i % 3 === 0 ? ' small' : '') + '"></div>' +
        '<div class="skeleton-time"></div>' +
      '</div>'
    ).join('') +
  '</div>';

  const messages = await api(`/api/accounts/${currentAccount}/contacts/${qq}/messages`);
  renderMessages(messages);
}
```

**Theme overrides for skeleton message colors** — same gradient approach as contact skeleton, matching each theme's background.

### 1.3 Theme Switching Spinner Overlay

When `switchTheme()` is called, show a brief full-content spinner overlay until the new CSS finishes loading.

**Implementation**:

Add CSS for the overlay:

```css
#theme-loading {
  position: fixed;
  inset: 0;
  z-index: 300;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255,255,255,0.6);
  transition: opacity 0.2s;
}

#theme-loading.hidden {
  display: none;
}

.theme-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #ddd;
  border-top-color: #999;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
```

Add the overlay element to the HTML (inside `#app`):

```html
<div id="theme-loading" class="hidden">
  <div class="theme-spinner"></div>
</div>
```

Update `switchTheme()`:

```javascript
function switchTheme(id, el) {
  currentTheme = id;
  const loading = document.getElementById('theme-loading');
  loading.classList.remove('hidden');

  const link = document.getElementById('theme-css');
  link.href = `/api/themes/${id}`;
  document.documentElement.setAttribute('data-theme', id);
  document.querySelectorAll('.theme-item').forEach(item => item.classList.remove('active'));
  el.classList.add('active');

  link.onload = () => {
    loading.classList.add('hidden');
  };

  // Fallback: hide after 1.5s even if onload doesn't fire
  setTimeout(() => {
    loading.classList.add('hidden');
  }, 1500);

  toggleThemePanel();
}
```

**Theme overrides for spinner** — `wechat.css` should use `background: rgba(0,0,0,0.5)` and lighter spinner colors.

---

## 2. Layout, Spacing, and Font Polish

### 2.1 Design Token Reference

Based on research into QQ and WeChat official design systems:

**QQ brand typography** (from Tencent QQ VI system by ISUX):
- Chinese: 方正兰亭黑 (FZLanTingHei) — not available as web font, fallback to `'PingFang SC', 'Microsoft YaHei', sans-serif`
- English: Helvetica Neue — fallback to `'Helvetica Neue', Helvetica, Arial, sans-serif`
- QQ brand blue: `#12B7F5` (Pantone 2995C)

**WeChat typography** (from WeUI design guidelines):
- System font stack: `-apple-system, BlinkMacSystemFont, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif`
- WeChat green: `#07C160`
- Chat bubble text: 17px on mobile, scaled to ~15px for desktop
- Line-height: 1.6 for body text

**Symbian QQ** (retro desktop era):
- 宋体 (SimSun) is period-accurate for Symbian S60
- Small, compact UI typical of early 2000s mobile

### 2.2 Font Stack Changes

**Current → Target** for each theme:

| Theme | Current `font-family` | Target `font-family` |
|-------|----------------------|---------------------|
| `symbian.css` | `'SimSun', '宋体', serif` | `'SimSun', '宋体', 'NSimSun', serif` (keep, period-accurate) |
| `modern_qq.css` | `-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', sans-serif` | `'PingFang SC', 'Helvetica Neue', 'Microsoft YaHei', 'Segoe UI', sans-serif` |
| `wechat.css` | `-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', sans-serif` | `-apple-system, BlinkMacSystemFont, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif` |

**Rationale**: Modern QQ should prioritize PingFang SC and Helvetica Neue to match QQ's brand VI. WeChat should use the WeUI-recommended system font stack. Symbian stays with SimSun for authenticity.

### 2.3 Spacing and Readability Improvements

**CRITICAL RULE**: Do NOT change `flex-direction`, element ordering, or DOM structure. Only adjust `padding`, `margin`, `gap`, `font-size`, `line-height`, `letter-spacing`, `border-radius`, and color values.

#### `modern_qq.css` Changes

| Selector | Property | Current | Target | Reason |
|----------|----------|---------|--------|--------|
| `html, body, #app` | `font-size` | `14px` | `14px` | Keep |
| `#sidebar-header` | `padding` | `12px` | `14px 12px` | More breathing room |
| `#sidebar-header select` | `padding` | `6px 10px` | `8px 12px` | Easier to tap |
| `#sidebar-header select` | `margin-bottom` | `8px` | `10px` | More spacing |
| `.contact-item` | `padding` | `10px 14px` | `12px 14px` | Less cramped |
| `.contact-item` | `gap` | `10px` | `12px` | More space between avatar and text |
| `.contact-name` | `font-size` | `14px` | `15px` | Better readability |
| `.contact-name` | `letter-spacing` | (none) | `0.3px` | Slightly airier |
| `.contact-preview` | `font-size` | `12px` | `12px` | Keep |
| `.contact-preview` | `line-height` | (none) | `1.4` | Better two-line preview |
| `#chat-header` | `padding` | `14px 20px` | `16px 24px` | More generous |
| `#chat-header` | `letter-spacing` | (none) | `0.5px` | Cleaner header text |
| `#chat-messages` | `padding` | `16px 20px` | `20px 24px` | More side margin |
| `.msg` | `margin-bottom` | `16px` | `18px` | More space between messages |
| `.msg-bubble` | `padding` | `10px 14px` | `10px 16px` | Slightly more horizontal padding |
| `.msg-bubble` | `line-height` | `1.6` | `1.7` | More readable for Chinese text |
| `.msg-bubble` | `letter-spacing` | (none) | `0.2px` | Better CJK readability |
| `.msg-time` | `font-size` | `10px` | `11px` | Slightly more legible |

#### `wechat.css` Changes

| Selector | Property | Current | Target | Reason |
|----------|----------|---------|--------|--------|
| `#sidebar-header` | `padding` | `12px` | `14px 12px` | More breathing room |
| `#sidebar-header select` | `padding` | `6px 10px` | `8px 12px` | Easier to tap |
| `.contact-item` | `padding` | `10px 14px` | `12px 14px` | Less cramped |
| `.contact-name` | `font-size` | `15px` | `15px` | Keep |
| `.contact-name` | `letter-spacing` | (none) | `0.3px` | Airier |
| `.contact-preview` | `line-height` | (none) | `1.4` | Better two-line preview |
| `#chat-header` | `padding` | `14px 20px` | `16px 24px` | More generous |
| `#chat-header` | `letter-spacing` | (none) | `0.3px` | Cleaner |
| `#chat-messages` | `padding` | `16px 20px` | `20px 24px` | More side margin |
| `.msg` | `margin-bottom` | `14px` | `16px` | More space between messages |
| `.msg-bubble` | `font-size` | `14px` | `15px` | WeChat desktop uses slightly larger text |
| `.msg-bubble` | `line-height` | `1.6` | `1.7` | More readable for Chinese text |
| `.msg-bubble` | `letter-spacing` | (none) | `0.2px` | Better CJK readability |
| `.msg-bubble` | `padding` | `9px 13px` | `10px 14px` | Slightly more generous |
| `.msg-time` | `font-size` | `10px` | `11px` | Slightly more legible |

#### `symbian.css` Changes

| Selector | Property | Current | Target | Reason |
|----------|----------|---------|--------|--------|
| `.contact-item` | `padding` | `8px 10px` | `10px 12px` | Less cramped while keeping retro compact feel |
| `.contact-name` | `letter-spacing` | (none) | `0.5px` | SimSun benefits from wider letter-spacing |
| `.contact-preview` | `line-height` | (none) | `1.3` | Better two-line preview |
| `#chat-messages` | `padding` | `12px` | `14px 16px` | Slightly more side margin |
| `.msg-bubble` | `line-height` | `1.5` | `1.6` | Better readability for Chinese text |
| `.msg-bubble` | `letter-spacing` | (none) | `0.3px` | SimSun is dense; needs more spacing |
| `.msg-time` | `font-size` | `10px` | `10px` | Keep (retro style is compact) |

### 2.4 Color Token Adjustments

Minor contrast and readability improvements only. No structural color changes.

#### `modern_qq.css`

| Selector | Property | Current | Target | Reason |
|----------|----------|---------|--------|--------|
| `.contact-preview` | `color` | `#999` | `#888` | Slightly more visible |
| `.contact-time` | `color` | `#bbb` | `#aaa` | More legible |
| `.msg-time` | `color` | `#ccc` | `#b0b0b0` | More legible |
| `.msg-label` | `color` | `#bbb` | `#aaa` | More legible |

#### `wechat.css`

| Selector | Property | Current | Target | Reason |
|----------|----------|---------|--------|--------|
| `.msg-label` | `color` | `#b2b2b2` | `#999` | More legible |
| `.msg-time` | `color` | `#b2b2b2` | `#999` | More legible |

#### `symbian.css`

No color changes — the retro palette is intentionally muted.

---

## 3. Theme Name Fix

### 3.1 Problem

The theme name is generated in `server.py`'s `get_themes()` endpoint:

```python
themes.append({
    'id': name,
    'name': name.replace('_', ' ').title(),
})
```

`name.replace('_', ' ').title()` converts `"modern_qq"` to `"Modern Qq"` because `.title()` capitalizes the first letter after every space, treating `qq` as a word that gets title-cased to `Qq`.

### 3.2 Fix

Replace the dynamic name generation with a lookup map in `server.py`:

```python
THEME_NAMES = {
    'symbian': 'Symbian QQ',
    'modern_qq': 'Modern QQ',
    'wechat': 'WeChat',
}

@app.route('/api/themes')
def get_themes():
    themes_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web', 'themes')
    themes = []
    if os.path.isdir(themes_dir):
        for f in os.listdir(themes_dir):
            if f.endswith('.css'):
                name = f.replace('.css', '')
                themes.append({
                    'id': name,
                    'name': THEME_NAMES.get(name, name.replace('_', ' ').title()),
                })
    return jsonify(themes)
```

This ensures:
- `symbian` → "Symbian QQ" (not "Symbian")
- `modern_qq` → "Modern QQ" (not "Modern Qq")
- `wechat` → "WeChat" (not "Wechat")
- Any future theme falls back to the old `.title()` logic

---

## 4. Language Switch Label

### 4.1 Problem

Current behavior in `toggleLang()`:

```javascript
document.getElementById('btn-lang').textContent = currentLang === 'zh' ? 'EN' : '中';
```

This shows the **opposite** language (what you can switch **to**), not the current language. The requirement is to show the **current** language.

### 4.2 Fix

Change the logic to show the current language:

```javascript
document.getElementById('btn-lang').textContent = currentLang === 'zh' ? '中' : 'EN';
```

Also update the initial state. The HTML currently has:

```html
<button id="btn-lang" title="Switch Language">EN</button>
```

Since `currentLang` starts as `'zh'`, the initial button text should be `'中'`:

```html
<button id="btn-lang" title="Switch Language">中</button>
```

---

## 5. Implementation Order

1. **Theme name fix** (item 3) — single-line change in `server.py`, zero risk
2. **Language switch label** (item 4) — two-line change in `index.html`, zero risk
3. **Skeleton screens** (item 1) — add CSS + modify `selectAccount()` and `selectContact()` in `index.html`
4. **Theme switching spinner** (item 1) — add overlay element + modify `switchTheme()` in `index.html`
5. **Font stack updates** (item 2) — modify `font-family` in each theme CSS
6. **Spacing and readability** (item 2) — adjust padding/margin/gap/font-size per theme CSS
7. **Color token adjustments** (item 2) — minor color tweaks per theme CSS

---

## 6. Files Modified

| File | Changes |
|------|---------|
| `server.py` | Add `THEME_NAMES` lookup map, update `get_themes()` |
| `web/index.html` | Add skeleton CSS + spinner CSS + overlay HTML; modify `selectAccount()`, `selectContact()`, `switchTheme()`, `toggleLang()`; update initial `btn-lang` text |
| `web/themes/symbian.css` | Font stack, spacing, readability, skeleton colors |
| `web/themes/modern_qq.css` | Font stack, spacing, readability, color tokens, skeleton colors |
| `web/themes/wechat.css` | Font stack, spacing, readability, color tokens, skeleton colors, spinner overlay color |

---

## 7. Testing Checklist

- [ ] Contact list shows skeleton while loading, then renders contacts
- [ ] Chat messages show skeleton while loading, then renders messages
- [ ] Theme switching shows spinner overlay, hides when CSS loads
- [ ] Spinner fallback hides after 1.5s even if CSS load event doesn't fire
- [ ] Skeleton shimmer animation works in all three themes
- [ ] Theme panel shows "Modern QQ" (not "Modern Qq"), "Symbian QQ" (not "Symbian"), "WeChat" (not "Wechat")
- [ ] Language button shows "中" when in Chinese mode, "EN" when in English mode
- [ ] Font stacks render correctly on Windows (Microsoft YaHei) and macOS (PingFang SC)
- [ ] Spacing changes improve readability without breaking layout
- [ ] No flex-direction, element order, or DOM structure changes
- [ ] All three themes render correctly after changes
