import asyncio
import datetime
import inspect
from dataclasses import dataclass, field
from zoneinfo import ZoneInfo

available_days = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday"
]

available_modes = [
    "now",
    "once",
    "every"
]

@dataclass
class Task:
    name: str
    callback: callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    # mode|day|time
    # mode: now, once, every
    # day: none, monday, tuesday, wednesday, thursday, friday, saturday, sunday
    # time: HH:MM:SS
    # If day is none, then day is not checked
    # If mode is now, then day and time are not checked
    rule: str = None
    ready: bool = False
    timezone: ZoneInfo = field(default=ZoneInfo("UTC"))
    time_pattern: str = "%H:%M:%S"
    date_pattern: str = "%d.%m.%Y"

    def set_time_settings(self, info: "SchedulerSettings"):
        self.timezone = info.timezone
        self.time_pattern = info.time_pattern
        self.date_pattern = info.date_pattern

    def check(self):
        if len(self.rule.split("|")) != 3:
            raise ValueError("Rule must have 3 parts separated by |")
        if self.mode not in available_modes:
            raise ValueError(f"Mode must be one of {available_modes}")
        if self.expired():
            self.ready = True
            print(f"WARN: Задача уже просрочена; {self}")
        _day = self.rule.split("|")[1]
        if self.mode == "every":
            if _day not in available_days and _day != "none":
                raise ValueError(f"Day must be one of {available_days} or none")
        else:
            try:
                datetime.datetime.strptime(_day, self.date_pattern)
            except ValueError:
                raise ValueError(f"Day ({_day}) must be in format {self.date_pattern}")
        try:
            datetime.datetime.strptime(self.rule.split("|")[2], self.time_pattern)
        except ValueError:
            raise ValueError(f"Time ({self.rule.split("|")[2]}) must be in format {self.time_pattern}")

    @property
    def mode(self):
        return self.rule.split("|")[0]

    @property
    def date(self):
        if self.mode == "every":
            return self.rule.split("|")[1]
        return datetime.datetime.strptime(self.rule.split("|")[1], "%d.%m.%Y").date()

    @property
    def time(self):
        return datetime.datetime.strptime(self.rule.split("|")[2], "%H:%M:%S").time()

    def get_rule(self):
        return self.mode, self.date, self.time

    def expired(self):
        if self.ready:
            return True
        if not self.rule:
            return True
        mode, date, time = self.get_rule()
        if mode == "once":
            today = datetime.datetime.now().astimezone(self.timezone)
            if today.date() > date:
                return True
            if date == today.date():
                if today.time() > time:
                    return True
        return False

    def __str__(self):
        return f"Task({self.name!r}; {self.rule!r}; {self.ready};)"

    async def run(self):
        if self.ready:
            return False, None
        if self.expired():
            return False, None
        try:
            if inspect.iscoroutinefunction(self.callback):
                callback_data = await self.callback(*self.args, **self.kwargs)
            else:
                callback_data = self.callback(*self.args, **self.kwargs)
            if self.mode != "every":
                self.ready = True
            print(f"Задача выполнена. {self}")
            return True, callback_data
        except Exception as e:
            return False, e

@dataclass
class SchedulerSettings:
    timezone: ZoneInfo = field(default=ZoneInfo("Europe/Moscow"))
    notify_day_at: str = "07:00:00"
    time_pattern: str = "%H:%M:%S"
    date_pattern: str = "%d.%m.%Y"
    prune_rule: str = "every|none|00:00:00"

    def __post_init__(self):
        if isinstance(self.timezone, str):
            self.timezone = ZoneInfo(self.timezone)


class Scheduler:
    def __init__(self, settings: SchedulerSettings, loop: asyncio.AbstractEventLoop):
        self.run = True
        self.loop = loop
        self.settings = settings
        self.lock = asyncio.Lock()
        self.tasks: list[Task] = []
        self.t = None
        self.notified = False

    def add_task(self, *tasks: Task):
        for task in tasks:
            if not isinstance(task, Task):
                raise ValueError("Task must be an instance of Task")
            task.set_time_settings(self.settings)
            task.check()
            if task.ready:
                continue
            print(f"Задача {task.name!r} добавлена в планировщик. Правило: {task.get_rule()!r}")
            self.tasks.append(task)

    async def tick(self, *_, **__):
        if not self.notified:
            print("Планировщик запущен")
            self.notified = True
        today = datetime.datetime.now().astimezone(self.settings.timezone)
        async with self.lock:
            for task in self.tasks.copy():
                if task.expired():
                    return
                mode, date, time = task.get_rule()
                if mode == "now":
                    return await task.run()
                if time != today.time():
                    return
                if mode == "every":
                    if date != "none":
                        if date.lower() != available_days[today.weekday()]:
                            return
                if mode == "once":
                    if date != today.date():
                        return
                return await task.run()

    async def _ticker(self):
        while self.run:
            await asyncio.sleep(0.7)
            await self.tick()
        print("Планировщик остановлен")

    def _prune(self):
        self.tasks = [task for task in self.tasks if not task.ready]

    def add_prune_task(self):
        t = Task("Очистка планировщика", self._prune, rule=self.settings.prune_rule)
        self.add_task(t)

    async def start(self):
        self.add_prune_task()
        await self._ticker()

    async def stop(self):
        print("Остановка планировщика...")
        self.run = False
        if self.t:
            await asyncio.gather(self.t)
