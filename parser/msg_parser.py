import struct
import os
from models import Message, Contact, Account
from parser.emoticon_decoder import decode_emoticons_in_text

_TIMESTAMP_MIN = 946684800
_TIMESTAMP_MAX = 1893456000


def parse_msg_info(file_path: str) -> list[Message]:
    with open(file_path, 'rb') as f:
        data = f.read()

    messages = []
    pos = 0
    while pos < len(data) - 2:
        if data[pos] not in (0xA8, 0xA9):
            pos += 1
            continue

        marker = data[pos:pos + 2]
        pos += 2

        if pos + 11 > len(data):
            break

        timestamp = struct.unpack('>I', data[pos:pos + 4])[0]

        if timestamp < _TIMESTAMP_MIN or timestamp > _TIMESTAMP_MAX:
            pos -= 1
            continue

        pos += 4
        pos += 6

        flag = data[pos]

        if flag & 0x0F != 0:
            pos -= 9
            continue

        pos += 1

        content_bytes = b''
        while pos < len(data) - 1:
            if data[pos:pos + 2] == marker:
                if pos + 2 <= len(data):
                    pos += 2
                break
            content_bytes += bytes([data[pos]])
            pos += 1

        try:
            text = content_bytes.decode('utf-16-le', errors='replace')
        except Exception:
            text = repr(content_bytes)

        text = decode_emoticons_in_text(text)

        if flag == 0x80:
            direction = 'sent'
        elif flag == 0x50:
            direction = 'system'
        else:
            direction = 'received'

        messages.append(Message(
            timestamp=timestamp,
            direction=direction,
            content=text,
            marker=marker,
        ))

    return messages


def scan_account(chat_dir: str) -> Account:
    account_name = os.path.basename(chat_dir)
    account = Account(qq_number=account_name, chat_dir=chat_dir)

    for entry in os.listdir(chat_dir):
        contact_dir = os.path.join(chat_dir, entry)
        if not os.path.isdir(contact_dir):
            continue
        msg_file = os.path.join(contact_dir, 'msg.info')
        if not os.path.isfile(msg_file):
            continue

        messages = parse_msg_info(msg_file)
        image_files = []
        for f in os.listdir(contact_dir):
            if f.endswith('.png') or f.endswith('.png.m'):
                image_files.append(os.path.join(contact_dir, f))

        contact = Contact(
            qq_number=entry,
            account_qq=account_name,
            messages=messages,
            image_files=image_files,
        )
        account.contacts.append(contact)

    account.contacts.sort(key=lambda c: c.messages[-1].timestamp if c.messages else 0, reverse=True)
    return account


def scan_all_accounts(base_dir: str) -> list[Account]:
    accounts = []
    for entry in os.listdir(base_dir):
        account_dir = os.path.join(base_dir, entry)
        if os.path.isdir(account_dir):
            try:
                account = scan_account(account_dir)
                if account.contacts:
                    accounts.append(account)
            except Exception:
                pass
    return accounts