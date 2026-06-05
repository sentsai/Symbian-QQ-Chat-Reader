import json
import os
import threading

_lock = threading.Lock()


def get_aliases_path(account_dir: str) -> str:
    return os.path.join(account_dir, 'aliases.json')


def load_aliases(account_dir: str) -> dict[str, str]:
    path = get_aliases_path(account_dir)
    if not os.path.isfile(path):
        return {}
    with _lock:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}


def save_alias(account_dir: str, qq_number: str, alias: str) -> dict[str, str]:
    with _lock:
        aliases = {}
        path = get_aliases_path(account_dir)
        if os.path.isfile(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    aliases = json.load(f)
            except (json.JSONDecodeError, OSError):
                aliases = {}
        aliases[qq_number] = alias
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(aliases, f, ensure_ascii=False, indent=2)
    return aliases


def delete_alias(account_dir: str, qq_number: str) -> dict[str, str]:
    with _lock:
        aliases = {}
        path = get_aliases_path(account_dir)
        if os.path.isfile(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    aliases = json.load(f)
            except (json.JSONDecodeError, OSError):
                aliases = {}
        aliases.pop(qq_number, None)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(aliases, f, ensure_ascii=False, indent=2)
    return aliases
