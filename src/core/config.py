import json
from collections import defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Literal

# 10.2024
AvailableFind = (
    # Очное отделение
    "1 курс ОФО",
    "2 курс ОФО",
    "3 курс ОФО",
    "4 курс ОФО",
    # Очно-Заочное отделение
    "1 курс ОЗФО",
    "2 курс ОЗФО",
    "3 курс ОЗФО",
    "4 курс ОЗФО",
    # Заочное отделение; На момент кода тут только 5 курс
    # "1 курс ЗФО",
    # "2 курс ЗФО",
    # "3 курс ЗФО",
    # "4 курс ЗФО",
    "5 курс ЗФО"
)

AvailableSheetOFO = (
    # Очное отделение 1 курс
    "1к Экономика",
    "1к Менеджмент",
    "1к Бизнес-информатика",
    "1к Прикладная математика",
    # Очное отделение 2 курс
    "2к Экономика",
    "2к Менеджмент",
    "2к Бизнес-информатика",
    "2к Прикладная математика",
    # Очное отделение 3 курс
    "3к Экономика",
    "3к Менеджмент",
    "3к Бизнес-информатика",
    "3к Прикладная математика",
    # Очное отделение 4 курс
    "4к Экономика",
    "4к Менеджмент",
    "4к Бизнес-информатика"
)

AvailableSheetOZFO = (
    # Очно-Заочное отделение 1 курс
    "1к Экономика",
    "1к Экономика ЭУП",
    "1к Менеджмент",
    "1к Менеджмент ЭУП",
    "1к Бизнес-информатика",
    "1к Прикладная математика",
    # Очно-Заочное отделение 2 курс
    "2к Экономика",
    "2к Экономика ЭУП",
    "2к Менеджмент",
    "2к Менеджмент ЭУП",
    "2к Бизнес-информатика",
    "2к Прикладная математика",
    # Очно-Заочное отделение 3 курс
    "3к Экономика",
    "3к Экономика ЭУП",
    "3к Менеджмент",
    "3к Бизнес-информатика",
    # Очно-Заочное отделение 4 курс
    "4к Экономика",
    "4к Менеджмент",
    "4к Бизнес-информатика",
)

AvailableSheetZFO = (
    # Заочное отделение 5 курс
    "5к Экономика",
    "5к Менеджмент",
)


@dataclass
class ChatConfig:
    url: str
    find: str
    sheet_name: str

    @property
    def ofo(self):
        if self.find:
            return "ОФО" in self.find
        return False

    @classmethod
    def check_find(cls, data):
        if data not in AvailableFind:
            return False
        return True

    def fix_sheet(self, data):
        if self.ofo:
            data = data.replace("НЧН", "").replace("ЧН", "").strip()
        return data

    def check_sheet(self, data: str):
        data = self.fix_sheet(data)
        if data not in AvailableSheetOFO + AvailableSheetOZFO + AvailableSheetZFO:
            return False
        return True

    def ready(self):
        if not self.url:
            return False
        if not self.find:
            return False
        if not self.sheet_name:
            return False
        return True

class Config:

    def __init__(self, global_config, per_chat_config):
        self.global_config = Path(global_config)
        self.per_chat_config = Path(per_chat_config)

        self.global_raw = {
            "token": None,
            "save_path": "./downloads/",
            "admins": [],  # тот кто может менять save_path
            "default": {
                "url": "http://www.fa.ru/fil/krasnodar/student/Pages/schedule.aspx",
                "find": None,
                "sheet_name": None,
            }
        }
        self.per_chat: dict[int, ChatConfig] = defaultdict(lambda: ChatConfig(**self.global_raw["default"]))

        if not self.global_config.exists() or not self.per_chat_config.exists():
            self._write()
        self._read()
        if not self.save_path.exists():
            self.save_path.mkdir()

    @property
    def token(self):
        return self.global_raw["token"]

    @property
    def admins(self):
        return self.global_raw["admins"]

    @property
    def save_path(self):
        return Path(self.global_raw["save_path"])

    @save_path.setter
    def save_path(self, value):
        self.global_raw["save_path"] = value
        self._write()

    def _write(self):
        self.global_config.write_text(json.dumps(self.global_raw, indent=4), "utf-8")
        self.per_chat_config.write_text(json.dumps({k: asdict(v) for k, v in self.per_chat.items()}, indent=4), "utf-8")

    def _read(self):
        self.global_raw = json.loads(self.global_config.read_text("utf-8"))
        for k, v in json.loads(self.per_chat_config.read_text("utf-8")).items():
            self.per_chat[int(k)] = ChatConfig(**v)

    def save(self):
        self._write()

    def get(self, chat_id):
        return self.per_chat[chat_id]

