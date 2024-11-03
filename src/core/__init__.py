templates = {
    "basic": {
        "type": "HTML",
        "ints":["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"],
        "rename": {},
        "header": "<b>Неделя:</b> {week_str}",
        "body": (
            "<b>{sdate} {sname}</b>\n"
            "<b>{i}. {lesson_time}</b> - {lesson_name}\n"
            "<i>Преподаватель:</i> {lesson_teacher}\n"
            "<i>Местоположение:</i> {lesson_place}\n"
        ),
        "not_ofo": [ # 1 - есть ссылка; 2 - нет ссылки
            '<i>Ссылка:</i> <a href="{lesson_link}">Подключится</a>',
            "<i>Ссылка:</i> <b>Ссылки нет в базе.</b>"
        ],
        "no_lessons": "<b>Нет пар</b>",
        "spacing": "\n\n",
        "day_now": "",
        "lesson": ""
    },
    "cringe": {
        "type": "HTML",
        "ints": ["", "❶", "❷", "❸", "❹", "❺", "❻", "❼", "❽", "❾", ],
        "rename": {"ВК": "Контора пидорасов"},
        "header": "<b>֍Неделя:</b> {week_str}֎",
        "body": (
            "<b>→ ̸ {sdate} ― {sname}</b>\n"
            "<b>{i}. {lesson_time}</b> - {lesson_name}\n"
            "<i>Препод:</i> {lesson_teacher}\n"
            "<i>Где?:</i> {lesson['place']}\n"
        ),
        "not_ofo": [ # 1 - есть ссылка; 2 - нет ссылки
            '<i>На, покури:</i> <a href="{lesson_link}">҉</a>',
            "<i>Ссылка:</i> <b>Ссылки нет, иди нахуй.</b>"
        ],
        "no_lessons": "<b>©Сегодня чилл (полный)</b>",
        "spacing": "\n\n",
        "day_now": "",
        "lesson": ""
    }
}


def render_data(data, ofo=True, template="basic"):
    template = templates.get(template)
    if not template:
        return f"Шаблон `{template}` - не доступен.", "Markdown"
    s = template["header"].format(week_str=data[-1]) + template["spacing"]
    for day in data:
        if isinstance(day, str):
            continue
        date = day['date'].replace("  ", " ")
        sdate, sname = date.split(" ", 1)
        s += template["day_now"].format(sdate=sdate, sname=sname) + template["spacing"]
        lessons = False
        for i, lesson in enumerate(day['lessons']):
            if lesson['name'] is None:
                continue
            lessons = True
            lesson_name = lesson['name']
            lesson_time = lesson['time']
            lesson_teacher = lesson['teacher']
            lesson_place = lesson['place']
            i = template["ints"][i]
            for k, v in template["rename"].items():
                lesson_name = lesson_name.replace(k, v)
                lesson_teacher = lesson_teacher.replace(k, v)
                lesson_place = lesson_place.replace(k, v)
                lesson_time = lesson_time.replace(k, v)
            s += template["body"].format(
                sdate=sdate,
                sname=sname,
                i=i,
                lesson_time=lesson_time,
                lesson_name=lesson_name,
                lesson_teacher=lesson_teacher,
                lesson_place=lesson_place
            )
            if ofo:
                lesson_link = lesson['link']
                if lesson_link:
                    s += template["not_ofo"][0].format(lesson_link=lesson_link)
                else:
                    s += template["not_ofo"][1]
            s += template["spacing"]
        if not lessons:
            s += template["no_lessons"] + template["spacing"]

    return s, template["type"]
