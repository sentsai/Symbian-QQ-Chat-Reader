import os
from flask import Flask, jsonify, send_file, request, Response
from parser.msg_parser import scan_all_accounts, scan_account, parse_msg_info
from parser.bmp_reader import read_bmp
from parser.mbm_decoder import decode_mbm
from parser.avatar_resolver import resolve_avatar
from models import Message, Contact, Account

app = Flask(__name__, static_folder='web', static_url_path='')

CHAT_HISTORY_DIR = ''
_DIR_MODE = 'root'


def _is_account_dir(path: str) -> bool:
    try:
        for entry in os.listdir(path):
            sub = os.path.join(path, entry)
            if os.path.isdir(sub) and os.path.isfile(os.path.join(sub, 'msg.info')):
                return True
    except OSError:
        pass
    return False


def _is_root_dir(path: str) -> bool:
    try:
        for entry in os.listdir(path):
            sub = os.path.join(path, entry)
            if os.path.isdir(sub) and _is_account_dir(sub):
                return True
    except OSError:
        pass
    return False


def _is_valid_chat_dir(path: str) -> bool:
    return _is_account_dir(path) or _is_root_dir(path)


def _scan_directory(path: str) -> list[Account]:
    if _is_account_dir(path):
        account = scan_account(path)
        return [account] if account.contacts else []
    return scan_all_accounts(path)


def _account_dir(account_qq: str) -> str:
    if _DIR_MODE == 'account':
        return CHAT_HISTORY_DIR
    return os.path.join(CHAT_HISTORY_DIR, account_qq)


def _contact_dir(account_qq: str, contact_qq: str) -> str:
    if _DIR_MODE == 'account':
        return os.path.join(CHAT_HISTORY_DIR, contact_qq)
    return os.path.join(CHAT_HISTORY_DIR, account_qq, contact_qq)


def _serialize_message(msg: Message) -> dict:
    return {
        'timestamp': msg.timestamp,
        'direction': msg.direction,
        'content': msg.content,
        'time_str': msg.time_str,
        'is_sent': msg.is_sent,
        'is_received': msg.is_received,
        'is_system': msg.is_system,
    }


def _serialize_contact(contact: Contact) -> dict:
    last_msg = contact.last_message
    return {
        'qq_number': contact.qq_number,
        'avatar_url': contact.avatar_url,
        'message_count': contact.message_count,
        'image_files': [os.path.relpath(f, CHAT_HISTORY_DIR).replace('\\', '/') for f in contact.image_files],
        'last_message': _serialize_message(last_msg) if last_msg else None,
    }


def _serialize_account(account: Account) -> dict:
    return {
        'qq_number': account.qq_number,
        'contact_count': len(account.contacts),
        'contacts': [_serialize_contact(c) for c in account.contacts],
    }


@app.route('/')
def index():
    return send_file('web/index.html')


@app.route('/api/config')
def get_config():
    return jsonify({
        'chat_history_dir': CHAT_HISTORY_DIR,
        'has_valid_dir': bool(CHAT_HISTORY_DIR) and _is_valid_chat_dir(CHAT_HISTORY_DIR),
    })


@app.route('/api/accounts')
def get_accounts():
    if not CHAT_HISTORY_DIR or not _is_valid_chat_dir(CHAT_HISTORY_DIR):
        return jsonify([])
    accounts = _scan_directory(CHAT_HISTORY_DIR)
    return jsonify([_serialize_account(a) for a in accounts])


@app.route('/api/accounts/<qq>/contacts')
def get_contacts(qq):
    if not CHAT_HISTORY_DIR:
        return jsonify([]), 404
    accounts = _scan_directory(CHAT_HISTORY_DIR)
    for acc in accounts:
        if acc.qq_number == qq:
            return jsonify([_serialize_contact(c) for c in acc.contacts])
    return jsonify([]), 404


@app.route('/api/accounts/<qq>/contacts/<friend_qq>/messages')
def get_messages(qq, friend_qq):
    if not CHAT_HISTORY_DIR:
        return jsonify([]), 404
    msg_file = os.path.join(_contact_dir(qq, friend_qq), 'msg.info')
    if not os.path.isfile(msg_file):
        return jsonify([]), 404
    messages = parse_msg_info(msg_file)
    return jsonify([_serialize_message(m) for m in messages])


@app.route('/api/accounts/<qq>/contacts/<friend_qq>/search')
def search_messages(qq, friend_qq):
    keyword = request.args.get('q', '').strip()
    if not keyword:
        return jsonify({'results': [], 'total': 0})

    if not CHAT_HISTORY_DIR:
        return jsonify({'results': [], 'total': 0}), 404

    msg_file = os.path.join(_contact_dir(qq, friend_qq), 'msg.info')
    if not os.path.isfile(msg_file):
        return jsonify({'results': [], 'total': 0}), 404

    messages = parse_msg_info(msg_file)
    keyword_lower = keyword.lower()
    results = []

    for i, msg in enumerate(messages):
        if keyword_lower in msg.content.lower():
            content = msg.content
            idx = content.lower().find(keyword_lower)
            start = max(0, idx - 20)
            end = min(len(content), idx + len(keyword) + 30)
            snippet = content[start:end]
            if start > 0:
                snippet = '...' + snippet
            if end < len(content):
                snippet = snippet + '...'

            results.append({
                'index': i,
                'timestamp': msg.timestamp,
                'direction': msg.direction,
                'content': msg.content,
                'snippet': snippet,
                'is_sent': msg.is_sent,
                'is_received': msg.is_received,
                'is_system': msg.is_system,
            })

    return jsonify({
        'results': results,
        'total': len(results),
    })


@app.route('/api/images/<path:img_path>')
def get_image(img_path):
    if not CHAT_HISTORY_DIR:
        return jsonify({'error': 'No directory set'}), 404
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


@app.route('/api/avatar/<account_qq>/<contact_qq>')
def get_avatar(account_qq, contact_qq):
    if not CHAT_HISTORY_DIR:
        return jsonify({'error': 'No directory set'}), 404
    account_path = _account_dir(account_qq)
    file_path = resolve_avatar(account_path, account_qq, contact_qq)
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


def _pick_folder_pywebview():
    import webview
    window = app.config.get('WEBVIEW_WINDOW')
    if window is None:
        return ''
    result = window.create_file_dialog(webview.FileDialog.FOLDER)
    if result and len(result) > 0:
        return result[0]
    return ''


@app.route('/api/open-directory', methods=['POST'])
def open_directory():
    global CHAT_HISTORY_DIR, _DIR_MODE

    selected = _pick_folder_pywebview()
    if not selected:
        return jsonify({'changed': False, 'reason': 'cancelled'})

    if not _is_valid_chat_dir(selected):
        return jsonify({'changed': False, 'reason': 'invalid'})

    CHAT_HISTORY_DIR = selected
    if _is_account_dir(selected) and not _is_root_dir(selected):
        _DIR_MODE = 'account'
    else:
        _DIR_MODE = 'root'

    accounts = _scan_directory(CHAT_HISTORY_DIR)
    return jsonify({
        'changed': True,
        'accounts': [_serialize_account(a) for a in accounts],
    })


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


@app.route('/api/themes/<name>')
def get_theme_css(name):
    themes_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web', 'themes')
    css_file = os.path.join(themes_dir, f'{name}.css')
    if not os.path.isfile(css_file):
        return jsonify({'error': 'Theme not found'}), 404
    return send_file(css_file, mimetype='text/css')


if __name__ == '__main__':
    app.run(port=5000, debug=False)
