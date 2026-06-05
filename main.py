import sys
import os
import threading

import pythonnet
pythonnet.load()

import webview
from server import app

_window = None


def start_server():
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)


def main():
    global _window

    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    _window = webview.create_window(
        title='QQ Chat History Reader',
        url='http://127.0.0.1:5000',
        width=960,
        height=680,
        min_size=(640, 480),
        resizable=True,
    )

    app.config['WEBVIEW_WINDOW'] = _window

    webview.start()


if __name__ == '__main__':
    main()
