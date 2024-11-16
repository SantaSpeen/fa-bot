import datetime
import threading
from dataclasses import dataclass, field

available_days = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday"
]

@dataclass
class Task:
    name: str
    callback: callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    rule: str = None
    ready: bool = False

    def __str__(self):
        return f"Task({self.name!r}; {self.rule!r})"


class Scheduler:
    def __init__(self, config: dict[str, str]):
        self.run = True
        self.lock = False
        self.config = config
        self.thread = threading.Thread(target=self._worker)
        self.tasks: list[Task] = []

    def add_task(self, *tasks: Task):
        for task in tasks:
            print(f"Задача {task.name!r} добавлена в планировщик. Правило: {task.rule!r}")
            self.tasks.append(task)

    def _worker(self):
        while self.run:
            if self.lock:
                threading.Event().wait(1)
                continue
            today = datetime.datetime.now()
            for task in self.tasks.copy():
                if not task.rule:
                    continue
                mode, day, time = task.rule.split("|")
                if mode == "now":
                    task.ready = True
                    task.callback(*task.args, **task.kwargs)
                    continue
                if time != today.strftime(self.config["time_pattern"]):
                    continue
                if mode == "every":
                    if day != "none":
                        if day.lower() != available_days[today.weekday()]:
                            continue
                if mode == "once":
                    if day != today.strftime(self.config["date_pattern"]):
                        continue
                    task.ready = True
                task.callback(*task.args, **task.kwargs)
            threading.Event().wait(1)

    def _prune(self):
        self.tasks = [task for task in self.tasks if not task.ready]

    def start(self):
        t = Task("Очистка планировщика", self._prune, rule=self.config["prune_rule"])
        self.add_task(t)
        self.thread.start()

    def stop(self):
        print("Остановка планировщика...")
        self.run = False
        self.thread.join()
