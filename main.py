import sys
import os
import threading
import webview
from server import app

CHAT_HISTORY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chat-history')


def start_server():
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)


def main():
    if not os.path.isdir(CHAT_HISTORY_DIR):
        print(f'Chat history directory not found: {CHAT_HISTORY_DIR}')
        print('Please place chat history files in the "chat-history" directory.')
        sys.exit(1)

    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    webview.create_window(
        title='QQ Chat History Reader',
        url='http://127.0.0.1:5000',
        width=960,
        height=680,
        min_size=(640, 480),
        resizable=True,
    )
    webview.start()


if __name__ == '__main__':
    main()