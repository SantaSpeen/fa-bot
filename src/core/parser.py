import json
import os
import sys
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

from .config import ChatConfig
from .scheduler import Task

def fix_nan(x):
    if pd.isna(x):
        return None
    return x

@dataclass
class Lesson:
    num: int
    name: str = None
    teacher: str = None
    time: str = None
    place: str = None
    link: str = None

    @property
    def empty(self):
        return self.name is None

    def replace(self, old, new):
        if self.name:
            self.name = self.name.replace(old, new)
        if self.place:
            self.place = self.place.replace(old, new)

    @property
    def task_time(self):
        t_start = self.time.split("-")[0]
        h, m = map(int, t_start.split("."))
        if m < 5:
            h -= 1
            m = 55
        else:
            m -= 5
        return f"{h}:{m}:00"

    def __str__(self):
        return f"    L:{self.num} {self.time!r} {self.name!r} {self.teacher!r} {self.place!r} link:{bool(self.link)}"

@dataclass
class Day:
    day_name: str = field(default=None)
    date: str = field(default=None)
    lessons: list[Lesson] = field(default_factory=list)

    def set_date(self, date):
        date, day_name = date.replace("  ", " ").split(" ", 1)
        self.date = date
        self.day_name = day_name.lower().capitalize()

    def add_lesson(self, lesson: Lesson):
        self.lessons.append(lesson)

    def tasks(self, callback, chat_id, ofo):
        tasks = []
        for lesson in self.lessons:
            if lesson.empty:
                continue
            task = Task(
                f"I:{chat_id} D:{self.date} L:{lesson.num}",
                callback,
                args=(chat_id, ofo),
                rule=f"once|{self.date}|{lesson.task_time}"
            )
            tasks.append(task)
        return tasks

    @property
    def empty(self):
        return all(lesson.empty for lesson in self.lessons)

    def __str__(self):
        return f"  Day {self.date!r} with {len(self.lessons)} lessons;\n" + "\n".join(str(lesson) for lesson in self.lessons)

@dataclass
class Week:
    date: str
    days: list[Day] = field(default_factory=list)

    def add_day(self, day: Day):
        self.days.append(day)

    def tasks(self, callback_day, callback_lesson, chat_id, ofo, notify_day_at):
        tasks = []
        for day in self.days:
            tasks.append(Task(f"I:{chat_id} D:{day.date}", callback_day, args=(chat_id, ofo), rule=f"once|{day.date}|{notify_day_at}"))
            tasks.extend(day.tasks(callback_lesson, chat_id, ofo))
        return tasks

    def __str__(self):
        return f"Week {self.date!r} with {len(self.days)} days;\n" + "\n".join(str(day) for day in self.days)


class Parser:
    # Настройки
    row_start = 13 # Номер строки с которой начинаются данные
    row_end = 93  # Номер строки на которой заканчиваются данные

    col_week = 0  # A Номер столбца с неделей
    row_week = 8  # Номер строки с неделей

    col_date = 0  # A Номер столбца с датой
    col_num = 1  # B Номер столбца с номером пары
    col_time = 3  # D Номер столбца с временем
    col_name = 5  # E Номер столбца с названием предмета именем
    col_aud = 8 # I Номер столбца с аудиторией

    offset_teacher = 1  # через сколько после col_name будет имя лектора
    rows_lesson = 2  # Сколько строк занимает одна пара

    len_day = 16 # Длина дня в строках
    len_week = 5 # Длина недели в днях
    len_lessons = 8 # Количество пар в день

    def __init__(self, links_path: Path, save_path: Path):
        self.links_path = links_path
        self.save_path = save_path
        if not self.links_path.exists():
            raise FileNotFoundError(f"Links file not found: {self.links_path}")
        if not self.save_path.exists():
            raise FileNotFoundError(f"Save path not found: {self.save_path}")
        self._links = {}
        self._read()

        # список дней недели в строках
        self.week = [(self.row_start + self.len_day * i, self.row_start + self.len_day * (i + 1)) for i in range(self.len_week)]

    def _read(self):
        if not self.links_path.exists():
            print("ERR: Файл с ссылками не найден. Восстановите его и перезапустите.")
            sys.exit(1)
        try:
            self._links.update(json.loads(self.links_path.read_text("utf-8")))
            print("Файл с ссылками загружен.")
        except json.JSONDecodeError:
            print("ERR: Файл с ссылками поврежден. Восстановите его и перезапустите.")
            sys.exit(1)

    @property
    def links(self):
        return self._links

    def reload(self):
        if not self.links_path.exists():
            self.links_path.write_text(json.dumps(self._links), "utf-8")
            return "ERR: Файл с шаблонами не найден. Файл восстановлен."
        old = self._links.copy()
        self._links.clear()
        try:
            j = json.loads(self.links_path.read_text("utf-8"))
            if len(j) == 0:
                return "ERR: Файл с ссылками пуст. Изменения не применены."
            self._links.update(j)
            return "Ссылки перезагружены."
        except json.JSONDecodeError:
            self._links = old
            return "ERR: Файл с ссылками поврежден. Изменения не применены."

    def download(self, chat: ChatConfig, even_week: bool):
        response = requests.get(chat.url)
        if response.status_code == 200:
            # Парсим HTML-код страницы
            soup = BeautifulSoup(response.text, 'html.parser')

            # Ищем ссылку на файл с расписанием
            anchors = soup.find_all('a')
            link = [urllib.parse.unquote(a.get('href')) for a in anchors if
                    a.get('href') and a.get("href").endswith(".xls") and chat.find in a.text]

            if link:
                link = link[1 if even_week else 0]
                # Получаем полный URL файла
                file_url = "http://www.fa.ru" + link
                file_name = os.path.basename(link).replace("'", "").replace(" ", "_")
                file_path = self.save_path / file_name

                if os.path.exists(file_path):
                    print(f"Файл '{file_name}' уже существует.")
                    return file_path

                # Сохраняем файл на локальном диске
                with open(file_path, 'wb') as file:
                    file.write(requests.get(file_url).content)

                print(f"Файл '{file_name}' успешно скачан!")
                return file_path
            else:
                print("Ссылка на файл с расписанием не найдена.")
        else:
            print("Не удалось получить страницу.")
        return None

    def parse_xml(self, chat: ChatConfig, file_path, even_week=None):
        sheet_name = chat.sheet_name
        if even_week is False:
            sheet_name += " НЧН"
        if even_week is True:
            sheet_name += " ЧН"
        print(f"Читаю {sheet_name!r} в файле.")

        sheet_names = list(pd.read_excel(file_path, sheet_name=None).keys())
        if sheet_name not in sheet_names:
            return f"\nЛист `{sheet_name}` не доступен. Доступные листы: \n{'\n'.join(sheet_names)}\n"

        # Загружаем данные из .xls в DataFrame
        df = pd.read_excel(file_path, sheet_name=sheet_name)

        week = Week(df.iloc[self.row_week, self.col_week])
        for j, (start_day, end_day) in enumerate(self.week):  # Перебираем дни
            day = Day()
            c = 0  # class
            offset = 0  # offset
            for i in range(start_day, end_day):  # Перебираем пары
                if offset > 1:
                    offset = 0
                date = df.iloc[i, self.col_date]
                if offset == 0:
                    lesson = Lesson(c)
                    if not pd.isna(date):
                        day.set_date(date)
                    num = df.iloc[i, self.col_num]
                    if not pd.isna(num):
                        c = int(num) - 1
                    lesson.name = fix_nan(df.iloc[i, self.col_name])
                    lesson.time = fix_nan(df.iloc[i, self.col_time])
                    lesson.place = fix_nan(df.iloc[i, self.col_aud])
                    day.add_lesson(lesson)
                if offset == self.offset_teacher:
                    lesson = day.lessons[c]
                    lesson.teacher = fix_nan(df.iloc[i, self.col_name])
                    if lesson.teacher is not None:
                        lesson.teacher = lesson.teacher.lower().capitalize()
                        lesson.link = self.links.get(lesson.teacher.split(" ")[0].lower(), None)
                offset += 1
            week.add_day(day)
        return week

    def get_data(self, chat: ChatConfig, even_week: bool):
        file_path = self.download(chat, even_week)
        if file_path is None:
            return None
        return self.parse_xml(chat, file_path, even_week)

