import sys
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
acc_dir = os.path.join(base, acc_qq)
friend_dir = os.path.join(acc_dir, '999999')
os.makedirs(friend_dir, exist_ok=True)
with open(os.path.join(friend_dir, 'msg.info'), 'wb') as f:
    f.write(build_msg([(1300000000, 0x80, 'hello')]))

server.CHAT_HISTORY_DIR = base
server._DIR_MODE = 'root'

out_dir = tempfile.mkdtemp(prefix='qq_export_out_')

# First call - consume properly with response.close()
with server.app.test_client() as client:
    res = client.post('/api/export', json={'destination': out_dir, 'lang': 'zh'})
    print(f"Call 1 Status: {res.status_code}", flush=True)
    print(f"Call 1 data: {res.data!r}", flush=True)
    res.close()

print(f"Lock held after call 1: {server._export_lock.locked()}", flush=True)

# Second call
with server.app.test_client() as client:
    res = client.post('/api/export', json={'destination': out_dir, 'lang': 'zh'})
    print(f"Call 2 Status: {res.status_code}", flush=True)
    print(f"Call 2 Body: {res.get_json()}", flush=True)

shutil.rmtree(out_dir)
shutil.rmtree(base)
