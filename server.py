import os
import json
from flask import Flask, jsonify, send_file, request, Response
from parser.msg_parser import scan_all_accounts, parse_msg_info
from parser.bmp_reader import read_bmp
from parser.mbm_decoder import decode_mbm
from models import Message, Contact, Account

app = Flask(__name__, static_folder='web', static_url_path='')

CHAT_HISTORY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chat-history')


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


@app.route('/api/accounts')
def get_accounts():
    accounts = scan_all_accounts(CHAT_HISTORY_DIR)
    return jsonify([_serialize_account(a) for a in accounts])


@app.route('/api/accounts/<qq>/contacts')
def get_contacts(qq):
    accounts = scan_all_accounts(CHAT_HISTORY_DIR)
    for acc in accounts:
        if acc.qq_number == qq:
            return jsonify([_serialize_contact(c) for c in acc.contacts])
    return jsonify([]), 404


@app.route('/api/accounts/<qq>/contacts/<friend_qq>/messages')
def get_messages(qq, friend_qq):
    msg_file = os.path.join(CHAT_HISTORY_DIR, qq, friend_qq, 'msg.info')
    if not os.path.isfile(msg_file):
        return jsonify([]), 404
    messages = parse_msg_info(msg_file)
    return jsonify([_serialize_message(m) for m in messages])


def _is_image_path(path: str) -> bool:
    return path.endswith('.png') or path.endswith('.png.m')


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
        return Response(png_data, mimetype='image/png')
    except Exception as e:
        return jsonify({'error': str(e)}), 500


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
                    'name': name.replace('_', ' ').title(),
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