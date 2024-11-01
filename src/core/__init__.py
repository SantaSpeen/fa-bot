from .parser import parse_xls
from .find_url import download_file
from .config import Config


def render_data(data, ofo=True):
    s = f"<b>Неделя:</b> {data[-1]}\n\n"
    for day in data:
        if isinstance(day, str):
            continue
        date = day['date'].replace("  ", " ")
        sdate, sname = date.split(" ", 1)
        s += f"<b>{sdate} {sname.lower().capitalize()}</b>\n"

        lessons = False
        for i, lesson in enumerate(day['lessons']):
            if lesson['name'] is None:
                continue
            lessons = True
            s += (
                f"<b>{i}. {lesson['time']}</b> - {lesson['name']}\n"
                f"<i>Преподаватель:</i> {lesson['teacher'].lower().capitalize()}\n"
                f"<i>Местоположение:</i> {lesson['place']}\n"
            )
            if not ofo:
                if lesson['link']:
                    s += f'<i>Ссылка:</i> <a href="{lesson['link']}">Подключится</a>\n\n'
                else:
                    s += '<i>Ссылка:</i> <b>Ссылки нет в базе.</b>\n\n'
        if not lessons:
            s += "<b>Нет пар</b>\n\n"

    return s
