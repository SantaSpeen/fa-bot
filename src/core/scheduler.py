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


class Scheduler:
    def __init__(self):
        self.run = True
        self.thread = threading.Thread(target=self._worker)
        self.tasks: list[Task] = []

    def add_task(self, task: Task):
        print(f"Задача {task.name!r} добавлена в планировщик. Правило: {task.rule!r}")
        self.tasks.append(task)

    def _worker(self):
        while self.run:
            today = datetime.datetime.now()
            for task in self.tasks:
                if not task.rule:
                    continue
                mode, day, time = task.rule.split("|")
                if time != today.strftime("%H:%M:%S"):
                    continue
                if mode == "every":
                    if day != "none":
                        if day.lower() != available_days[today.weekday()]:
                            continue
                if mode == "once":
                    if day != today.strftime("%Y-%m-%d"):
                        continue
                    task.ready = True
                task.callback(*task.args, **task.kwargs)
            threading.Event().wait(1)

    def _prune(self):
        self.tasks = [task for task in self.tasks if not task.ready]

    def start(self):
        t = Task("Очистка планировщика", self._prune, rule="every|none|00:00:00")
        self.add_task(t)
        self.thread.start()

    def stop(self):
        print("Остановка планировщика...")
        self.run = False
        self.thread.join()

if __name__ == '__main__':
    import time as t

    s = Scheduler()
    try:
        s.start()
        while True:
            t.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        s.stop()
