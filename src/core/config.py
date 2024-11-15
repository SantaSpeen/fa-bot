import json
import sys
import traceback
from collections import defaultdict
from dataclasses import dataclass, asdict, field
from pathlib import Path

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
    template: str = field(default="basic")
    use_custom_template: bool = field(default=False)
    custom_template: dict = field(default_factory=dict)
    custom_links: dict = field(default_factory=dict)

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

    def save(self):
        pass

class Config:

    def __init__(self, global_config):
        self.config_file = Path(global_config)
        # self.chats_store = None
        self.__config_raw: dict[str, str | list[int] | dict[str, str | None]] = {
            "token": "TOKEN_HERE",
            "admins": [],  # тот кто может менять save_path + links, templates
            "save_path": "./downloads/",
            "chats_store": "./storage/chats.json",
            "links": "./storage/links.json",
            "templates": "./storage/templates.json",
            "default": {
                "url": "http://www.fa.ru/fil/krasnodar/student/Pages/schedule.aspx",
                "find": None,
                "sheet_name": None,
                "template": "basic"
            }
        }
        self.__init_config_file()
        self.__check()
        self.__chats: dict[int, ChatConfig] = defaultdict(lambda: ChatConfig(**self.__config_raw["default"]))
        self.chats_store = Path(self.__config_raw["chats_store"])
        self.__init_chats_store()

    def __init_config_file(self):
        if not self.config_file.exists():
            self.config_file.write_text(json.dumps(self.__config_raw, indent=4), "utf-8")
            print(f"Файл с конфигурацией создан: {self.config_file}.\nНастройте его и перезапустите.")
            sys.exit(0)
        try:
            _raw = json.loads(self.config_file.read_text("utf-8"))
            self.__config_raw.update(_raw)
            self.__config_raw['default'].update(_raw['default'])
        except json.JSONDecodeError:
            print(f"Файл с конфигурацией поврежден: {self.config_file}.\nНастройте его (или удалите для пересоздания) и перезапустите.")
            sys.exit(0)
        print("Файл с конфигурацией загружен.")

    def __check(self):
        if not self.__config_raw:
            return
        if self.token is None:
            print("ERR: Токен не указан.")
            exit(1)
        if len(self.token.split(":")) != 2:
            print("ERR: Токен указан неверно.")
            exit(1)
        try:
            ChatConfig(**self.__config_raw['default'])
        except TypeError:
            print("ERR: Настройки по умолчанию для чатов указаны неверно.")
            exit(1)
        if not self.admins:
            print("WARN: Администраторы не указаны.")
        print("Конфигурация проверена.")

    def __init_chats_store(self):
        if not self.chats_store.exists():
            self.chats_store.write_text(json.dumps({}), "utf-8")
            print(f"Файл с настройками чатов создан: {self.chats_store}.")
        try:
            for k, _v in json.loads(self.chats_store.read_text("utf-8")).items():
                v = self.__config_raw['default'].copy()
                v.update(_v)
                self.__chats[int(k)] = ChatConfig(**v)
        except json.JSONDecodeError or TypeError as e:
            print(f"Файл с чатами поврежден: {self.chats_store}.\nИсправьте его (или удалите для пересоздания) и перезапустите.")
            traceback.print_exc()
            sys.exit(1)
        print("Файл с настройками чатов загружен.")

    def reload_chats(self):
        old = self.__chats.copy()
        self.__chats.clear()
        try:
            for k, _v in json.loads(self.chats_store.read_text("utf-8")).items():
                v = self.__config_raw['default'].copy()
                v.update(_v)
                self.__chats[int(k)] = ChatConfig(**v)
            return "Настройки чатов перезагружены."
        except json.JSONDecodeError or TypeError:
            traceback.print_exc()
            self.__chats = old
            return f"Файл с чатами поврежден: {self.chats_store}. Изменения не применены."

    @property
    def token(self) -> str | None:
        return self.__config_raw["token"]

    @property
    def admins(self) -> list[int]:
        return self.__config_raw["admins"]

    @property
    def save_path(self) -> Path:
        return Path(self.__config_raw["save_path"])

    @save_path.setter
    def save_path(self, value):
        self.__config_raw["save_path"] = value
        self.save()

    @property
    def links(self) -> Path:
        return Path(self.__config_raw["links"])

    @links.setter
    def links(self, value):
        self.__config_raw["links"] = value
        self.save()

    @property
    def templates(self) -> Path:
        return Path(self.__config_raw["templates"])

    @templates.setter
    def templates(self, value):
        self.__config_raw["templates"] = value
        self.save()

    def save(self):
        self.config_file.write_text(json.dumps(self.__config_raw, indent=4), "utf-8")
        self.save_chats()

    def save_chats(self):
        with open(self.chats_store, "w", encoding="utf-8") as f:
            f.write(json.dumps({k: asdict(v) for k, v in self.__chats.items()}, indent=4))

    def get_chat(self, chat_id):
        return self.__chats[chat_id]
