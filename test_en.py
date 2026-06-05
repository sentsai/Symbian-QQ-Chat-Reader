import sys
import os
import tempfile
import shutil
import struct

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

out_en = tempfile.mkdtemp(prefix='qq_export_en_')
print(f"Before: out_en={out_en}, contents: {os.listdir(out_en)}", flush=True)
with server.app.test_client() as client:
    res = client.post('/api/export', json={'destination': out_en, 'lang': 'en'})
    print(f"EN Status: {res.status_code}", flush=True)
    # Force iteration of the response body
    data = res.data
    print(f"EN data: {data!r}", flush=True)
    res.close()

print(f"After: out_en={out_en}, contents: {os.listdir(out_en)}", flush=True)
for root, dirs, files in os.walk(out_en):
    for f in files:
        full = os.path.join(root, f)
        with open(full, 'rb') as fp:
            content = fp.read()
        print(f"FILE: {full}", flush=True)
        print(f"  content: {content.decode('utf-8-sig')!r}", flush=True)

shutil.rmtree(out_en)
shutil.rmtree(base)
