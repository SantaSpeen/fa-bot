import json
import sys
from dataclasses import dataclass
from pathlib import Path

from core import ChatConfig
from core.parser import Week, Day, Lesson


@dataclass
class Template:
    type: str
    nums: list[str]
    rename: dict[str, str]
    header: str
    day_header: str
    day_body: str
    link: list[str]
    no_lessons: str
    spacing: str
    lesson: str

    def render(self, obj, ofo: bool):
        if isinstance(obj, Week):
            return self._render_week(obj, ofo)
        if isinstance(obj, Day):
            return self._render_day(obj, ofo)
        if isinstance(obj, Lesson):
            return self._render_lesson(obj, ofo)
        return None

    def _render_week(self, week: Week, ofo: bool):
        s = self.header.format(week_str=week.date) + self.spacing
        for day in week.days:
            if isinstance(day, str):
                continue
            s += self._render_day(day, ofo)[0]
            if day.empty:
                s += self.spacing
        return s, self.type

    def _render_day(self, day: Day, ofo: bool):
        s = self.day_header.format(date=day.date, day_name=day.day_name)
        for i, lesson in enumerate(day.lessons):
            if lesson.empty:
                continue
            for old, new in self.rename.items():
                lesson.replace(old, new)
            s += self.day_body.format(
                i=self.nums[lesson.num],
                lesson_time=lesson.time,
                lesson_name=lesson.name,
                lesson_teacher=lesson.teacher,
                lesson_place=lesson.place
            )
            s += self.spacing
            if not ofo:
                if lesson.link:
                    s += self.link[0].format(lesson_link=lesson.link)
                else:
                    s += self.link[1]
                s += self.spacing
            s += self.spacing
        if day.empty:
            s += self.no_lessons
        return s, self.type

    def _render_lesson(self, lesson: Lesson, ofo: bool):
        s = self.lesson.format(
            i=self.nums[lesson.num],
            lesson_time=lesson.time,
            lesson_name=lesson.name,
            lesson_teacher=lesson.teacher,
            lesson_place=lesson.place,
        )
        if not ofo:
            s+= self.spacing
            if lesson.link:
                s += self.link[0].format(lesson_link=lesson.link)
            else:
                s += self.link[1]
        return s, self.type


class Templator:
    def __init__(self, templates_path: Path):
        self.templates_path = templates_path
        self.__templates_raw = {}
        self.__templates = {}
        self._read()

    def _read(self):
        if not self.templates_path.exists():
            print("ERR: Файл с шаблонами не найден. Восстановите его и перезапустите.")
            sys.exit(1)
        try:
            self.__templates_raw.update(json.loads(self.templates_path.read_text("utf-8")))
            self.__templates = {k: Template(**v) for k, v in self.__templates_raw.items()}
            print("Файл с шаблонами загружен.")
        except json.JSONDecodeError:
            print("ERR: Файл с шаблонами поврежден. Восстановите его и перезапустите.")
            sys.exit(1)

    def reload(self):
        if not self.templates_path.exists():
            self.templates_path.write_text(json.dumps(self.__templates_raw), "utf-8")
            return "ERR: Файл с шаблонами не найден. Файл восстановлен."
        old = self.__templates_raw.copy()
        self.__templates_raw.clear()
        try:
            j = json.loads(self.templates_path.read_text("utf-8"))
            if len(j) == 0:
                return "ERR: Файл с шаблонами пуст. Изменения не применены."
            self.__templates_raw.update()
            self.__templates = {k: Template(**v) for k, v in self.__templates_raw.items()}
            return "Файл с шаблонами загружен."
        except json.JSONDecodeError:
            self.__templates_raw = old
            return "ERR: Файл с шаблонами поврежден. Изменения не применены."

    @property
    def list(self) -> list[str]:
        return [f"{v}" for v in self.__templates_raw.keys() if isinstance(v, str)]

    def get(self, name_or_chat: str | ChatConfig) -> Template | None:
        name = name_or_chat
        if isinstance(name_or_chat, ChatConfig):
            name = name_or_chat.template
        if name not in self.list:
            return None
        return self.__templates.get(name)
