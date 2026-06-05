import os


def resolve_avatar(chat_dir: str, account_qq: str, contact_qq: str) -> str | None:
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
            ts_str = f[len(prefix):-6]
        elif f.endswith('.png'):
            ts_str = f[len(prefix):-4]
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

    for ts, f in candidates:
        if ts == best_ts and f.endswith('.png') and not f.endswith('.png.m'):
            return os.path.join(search_dir, f)

    return os.path.join(search_dir, candidates[0][1])
