import json
import os
import threading

_lock = threading.Lock()

_DEFAULTS = {
    'last_chat_dir': '',
    'sidebar_width': 280,
}


def get_config_path() -> str:
    return os.path.join(os.path.expanduser('~'), '.qq-chat-reader', 'config.json')


def load_config() -> dict:
    path = get_config_path()
    config = dict(_DEFAULTS)
    if os.path.isfile(path):
        with _lock:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                config.update(saved)
            except (json.JSONDecodeError, OSError):
                pass
    return config


def save_config(key: str, value) -> dict:
    with _lock:
        config = dict(_DEFAULTS)
        path = get_config_path()
        if os.path.isfile(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    config.update(json.load(f))
            except (json.JSONDecodeError, OSError):
                pass
        config[key] = value
        config_dir = os.path.dirname(path)
        os.makedirs(config_dir, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    return config
