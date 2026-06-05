import sys
import traceback
import os
import tempfile
import shutil
import struct
import time

sys.path.insert(0, r'd:\Dev-Projects\qq-chat-reader')

import server
from parser.alias_store import save_alias

def build_msg(messages):
    data = b''
    for ts, flag, text in messages:
        data += b'\xa8\xa8'
        data += struct.pack('>I', ts)
        data += b'\x00' * 6
        data += bytes([flag])
        data += text.encode('utf-16-le')
        data += b'\xa8\xa8'
    return data

base = tempfile.mkdtemp(prefix='qq_export_test_')
acc_qq = '123456'
friend_qq = '999999'
acc_dir = os.path.join(base, acc_qq)
friend_dir = os.path.join(acc_dir, friend_qq)
os.makedirs(friend_dir, exist_ok=True)

msgs = [
    (1300000000, 0x80, 'hello'),
    (1300000060, 0x20, 'hi there'),
]
with open(os.path.join(friend_dir, 'msg.info'), 'wb') as f:
    f.write(build_msg(msgs))

save_alias(acc_dir, friend_qq, '小明')

server.CHAT_HISTORY_DIR = base
server._DIR_MODE = 'root'

out_dir = tempfile.mkdtemp(prefix='qq_export_out_')
print(f"Out dir: {out_dir}", flush=True)
print(f"Out dir contents BEFORE: {os.listdir(out_dir)}", flush=True)

with server.app.test_client() as client:
    res = client.post('/api/export', json={'destination': out_dir, 'lang': 'zh'})
    print(f"Status: {res.status_code}", flush=True)
    print(f"Response data: {res.data!r}", flush=True)

time.sleep(1)
print(f"Out dir contents AFTER: {os.listdir(out_dir)}", flush=True)
for root, dirs, files in os.walk(out_dir):
    print(f"Walking {root}, dirs: {dirs}, files: {files}", flush=True)
    for f in files:
        full = os.path.join(root, f)
        with open(full, 'rb') as fp:
            data = fp.read()
        print(f"FILE: {full}, size: {len(data)}", flush=True)
        print(f"  hex: {data.hex()}", flush=True)
        print(f"  content: {repr(data.decode('utf-8-sig'))}", flush=True)

shutil.rmtree(out_dir)
shutil.rmtree(base)
