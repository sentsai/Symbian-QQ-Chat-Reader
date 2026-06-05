from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Message:
    timestamp: int
    direction: str
    content: str
    marker: bytes = field(repr=False)

    @property
    def time_str(self) -> str:
        return datetime.fromtimestamp(self.timestamp).strftime('%Y-%m-%d %H:%M:%S')

    @property
    def is_sent(self) -> bool:
        return self.direction == 'sent'

    @property
    def is_received(self) -> bool:
        return self.direction == 'received'

    @property
    def is_system(self) -> bool:
        return self.direction == 'system'


@dataclass
class Contact:
    qq_number: str
    account_qq: str = ''
    messages: list[Message] = field(default_factory=list)
    image_files: list[str] = field(default_factory=list)

    @property
    def avatar_url(self) -> str:
        return f'/api/avatar/{self.account_qq}/{self.qq_number}'

    @property
    def last_message(self) -> Message | None:
        return self.messages[-1] if self.messages else None

    @property
    def message_count(self) -> int:
        return len(self.messages)


@dataclass
class Account:
    qq_number: str
    contacts: list[Contact] = field(default_factory=list)
    chat_dir: str = ''
