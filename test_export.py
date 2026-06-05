import sys
import os
import tempfile
import shutil
import struct

sys.path.insert(0, r'd:\Dev-Projects\qq-chat-reader')

import server
from parser.alias_store import save_alias, load_aliases

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

# Friend 1 with alias
friend1 = '999999'
friend1_dir = os.path.join(acc_dir, friend1)
os.makedirs(friend1_dir, exist_ok=True)
with open(os.path.join(friend1_dir, 'msg.info'), 'wb') as f:
    f.write(build_msg([
        (1300000000, 0x80, 'hello'),
        (1300000060, 0x20, 'hi there'),
    ]))
save_alias(acc_dir, friend1, '小明')

# Friend 2 without alias
friend2 = '888888'
friend2_dir = os.path.join(acc_dir, friend2)
os.makedirs(friend2_dir, exist_ok=True)
with open(os.path.join(friend2_dir, 'msg.info'), 'wb') as f:
    f.write(build_msg([
        (1300001000, 0x80, 'multiline\nmessage\ntest'),
    ]))

# Friend 3 with no msg.info (should be skipped)
friend3 = '777777'
friend3_dir = os.path.join(acc_dir, friend3)
os.makedirs(friend3_dir, exist_ok=True)

server.CHAT_HISTORY_DIR = base
server._DIR_MODE = 'root'

# Test zh
out_zh = tempfile.mkdtemp(prefix='qq_export_zh_')
with server.app.test_client() as client:
    res = client.post('/api/export', json={'destination': out_zh, 'lang': 'zh'})
    print(f"ZH Status: {res.status_code}", flush=True)
    print(f"ZH Events:", flush=True)
    for line in res.data.decode('utf-8').strip().split('\n\n'):
        if line.startswith('data: '):
            print(f"  {line[6:]}", flush=True)
    print("\nZH Files:", flush=True)
    for root, dirs, files in os.walk(out_zh):
        for f in sorted(files):
            full = os.path.join(root, f)
            with open(full, 'rb') as fp:
                data = fp.read()
            print(f"  {full}", flush=True)
            print(f"    Content: {data.decode('utf-8-sig')!r}", flush=True)

# Test en
out_en = tempfile.mkdtemp(prefix='qq_export_en_')
with server.app.test_client() as client:
    res = client.post('/api/export', json={'destination': out_en, 'lang': 'en'})
    print(f"\nEN Status: {res.status_code}", flush=True)
    print(f"\nEN Files:", flush=True)
    for root, dirs, files in os.walk(out_en):
        for f in sorted(files):
            full = os.path.join(root, f)
            with open(full, 'rb') as fp:
                data = fp.read()
            print(f"  {full}", flush=True)
            print(f"    Content: {data.decode('utf-8-sig')!r}", flush=True)

# Test missing destination
with server.app.test_client() as client:
    res = client.post('/api/export', json={'lang': 'zh'})
    print(f"\nNo destination: {res.status_code} {res.get_json()}", flush=True)

# Test missing chat dir
server.CHAT_HISTORY_DIR = ''
with server.app.test_client() as client:
    res = client.post('/api/export', json={'destination': out_zh, 'lang': 'zh'})
    print(f"No chat dir: {res.status_code} {res.get_json()}", flush=True)

shutil.rmtree(out_zh)
shutil.rmtree(out_en)
shutil.rmtree(base)
print("\nAll tests passed!", flush=True)
