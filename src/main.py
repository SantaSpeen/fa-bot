import asyncio
import json
import os
import traceback

from telegram import Update, LinkPreviewOptions, InputFile
from telegram.ext import Application, MessageHandler, filters, ContextTypes

from core import Templator, Config, Parser

# /set find 1 курс ОЗФО
# /set sheet 1к Прикладная математика

help_msg = """\
Доступные команды:
  /auto - автоматический поиск и обработка файла
  /file - обработка файла из ответа на сообщение
  /settings - Настройки чата
Команды для настройки:
  (Для каждого чата настраивается отдельно)
  /set <команда> [[значение]]
  /template <команда> [[значение]]
{}
Использованные ресурсы:
- [Сайт МФИ](http://www.fa.ru/)
- [Бот](http://github.com/SantaSpeen/fa-bot)
"""
help_msg_admin = r"""
Админские команды:
    /set\_save\_path - установить путь для сохранения файлов
    /reload - перезагрузить данные (chats, links, templates)
"""

allow_set_cmds = ("help", "find", "sheet", "url")
set_help = """\
Использование: `/set <команда> [значение]`
Доступные команды:
  `help` - вывести это сообщение
  `url` - установить URL страницы с расписанием
  `find` - установить строку для поиска файла
  `sheet` - установить название листа в файле с расписанием
Пример:
 - `/set find 1 курс ОЗФО`
 - `/set sheet 1к Прикладная математика`
Что бы настройки: 
/settings\
"""

allow_template_cmds = ("help", "list", "use", "custom")
template_help = """\
Использование: `/template <команда> [значение]`
Доступные команды:
  `help` - Вывести это сообщение
  `list` - Вывести список доступных шаблонов
  `use` - Использовать шаблон из доступных
  `custom` - Загрузить свой шаблон (не доступно)
Пример:
  - `/template list`
  - `/template use default`\
"""

username = ""

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

config = Config("config.json")
templator = Templator(config.templates)
parser = Parser(config.links, config.save_path)

async def render_and_send(update, context, file, even_week):
    try:
        chat_id = update.effective_chat.id
        chat = config.get_chat(chat_id)
        data = parser.parse_xml(chat, file, even_week)
        # print(data)
        if not data:
            await update.message.reply_text('Ошибка при обработке файла.')
            return
        if isinstance(data, str):
            raise Exception(data)
        template = templator.get(chat)
        text, parse_mode = template.render(data, file.name)
        await context.bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)
    except Exception as e:
        traceback.print_exc()
        await update.message.reply_text(f'Ошибка при обработке файла: {e}', parse_mode='Markdown')
        os.remove(file)

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message and update.message.reply_to_message.document:
        mid = await update.message.reply_text("Загрузка и анализ файла..", parse_mode='Markdown')
        document = update.message.reply_to_message.document
        file_id = document.file_id
        new_file = await context.bot.get_file(file_id)
        if new_file.file_size > 5 * 1024 * 1024:
            await context.bot.editMessageText("Файл слишком большой (>5Mb)", mid.chat_id, mid.message_id, parse_mode='Markdown')
            return
        filename = document.file_name.replace("'","").replace(" ", "_")
        if not filename.endswith('.xls'):
            await context.bot.editMessageText("Файл должен быть в формате `.xls`", mid.chat_id, mid.message_id, parse_mode='Markdown')
            return
        file_path = config.save_path / filename
        if file_path.exists():
            print(f"Файл '{filename}' уже существует.")
        else:
            await new_file.download_to_drive(file_path)
            print(f"Файл '{filename}' успешно сохранен!")

        s = f'Документ сохранен: `{file_path.name}`.\nОбработка файла...'
        await context.bot.editMessageText(s, mid.chat_id, mid.message_id, parse_mode='Markdown')
        even_week = None
        if config.get_chat(update.message.chat.id).ofo:
            even_week = not "1" in update.message.text
        await render_and_send(update, context, file_path, even_week)
    else:
        await update.message.reply_text('Пожалуйста, ответьте на сообщение с документом.')

async def handle_auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not config.get_chat(update.effective_chat.id).ready():
        await update.message.reply_text("Настройки не установлены.")
        return
    if config.get_chat(update.effective_chat.id).ofo:
        await update.message.reply_text("Для ОФО нет поддержки так как админу лень делать поддержку 2х групп.\n"
                                        "Админ: @id0124\n"
                                        "Ссылка на проект для тех, кто хочет что-то изменить: [github](https://github.com/SantaSpeen/fa-bot)",
                                        parse_mode='Markdown', link_preview_options=LinkPreviewOptions(True))
        return
    mid = await update.message.reply_text("Поиск файла на сайте универа..", parse_mode='Markdown')
    chat = config.get_chat(update.effective_chat.id)
    even_week = None
    if chat.ofo:
        even_week = not "1" in update.message.text
    file_path = parser.download(chat, even_week)
    if not file_path:
        await context.bot.editMessageText('Ошибка при загрузке файла.', mid.chat_id, mid.message_id, parse_mode='Markdown')
        return
    s = f'Документ сохранен: `{file_path.name}`.\nОбработка файла...'
    await context.bot.editMessageText(s, mid.chat_id, mid.message_id, parse_mode='Markdown')
    await render_and_send(update, context, file_path, even_week)

async def handle_settings(update: Update):
    cmd = update.message.text.split(" ")
    cmd, setts = cmd[0], " ".join(cmd[1:])
    if not setts:
        await update.message.reply_text(
            "Ипользуйте команду в формате `/set <команда> <значение>`\n"
            f"Доступные команды: `{'`, `'.join(allow_set_cmds)}`", parse_mode='Markdown')
        return
    data = setts.split(" ", 1)
    subcmd = data[0]
    if subcmd not in allow_set_cmds:
        await update.message.reply_text(f"Недопустимая команда: `{subcmd}`")
        return
    if subcmd == "help":
        return await update.message.reply_text(set_help, parse_mode='Markdown')
    if len(data) == 1:
        await update.message.reply_text(f"Укажите значение для установки: `/set {subcmd} <значение>`", "Markdown")
        return
    set_data = data[1]
    chat = config.get_chat(update.message.chat.id)
    match subcmd:
        case "url":
            chat.url = set_data
            await update.message.reply_text(f"URL страницы с расписанием изменен на `{set_data}`", parse_mode='Markdown')
        case "find":
            if not chat.check_find(set_data):
                await update.message.reply_text(f"Недопустимое значение: `{set_data}`", parse_mode='Markdown')
                return
            chat.find = set_data
            await update.message.reply_text(f"Строка для поиска файла изменена на `{set_data}`", parse_mode='Markdown')
        case "sheet":
            if not chat.check_sheet(set_data):
                await update.message.reply_text(f"Недопустимое значение: `{set_data}`", parse_mode='Markdown')
                return
            chat.sheet_name = chat.fix_sheet(set_data)
            await update.message.reply_text(f"Название листа в файле с расписанием изменено на `{set_data}`. "
                                            f"{"Чётность недели убрана." if chat.sheet_name != set_data else ""}", parse_mode='Markdown')

async def handle_template(update: Update):
    cmd = update.message.text.split(" ")
    cmd, setts = cmd[0], " ".join(cmd[1:])
    if not setts:
        await update.message.reply_text(
            "Ипользуйте команду в формате `/template <команда> [значение]`\n"
            f"Доступные команды: `{'`, `'.join(allow_template_cmds)}`", parse_mode='Markdown')
        return
    data = setts.split(" ", 1)
    subcmd = data[0]
    if subcmd not in allow_template_cmds:
        await update.message.reply_text(f"Недопустимая команда: `{subcmd}`")
        return
    chat = config.get_chat(update.message.chat.id)
    match subcmd, len(data):
        case "help", _:
            await update.message.reply_text(template_help, parse_mode='Markdown')
        case "list", 1:
            _s = ""
            for tem in templator.list:
                _s += f"  - `{tem}`\n"
            s = f"Доступные шаблоны:\n{_s}"
            await update.message.reply_text(s, "Markdown")
        case "use", 2:
            set_data = data[1]
            if set_data in templator.list:
                await update.message.reply_text(f"Установлено новое значение: `{chat.template}` > `{set_data}`", 'Markdown')
                chat.template = set_data
                return
            await update.message.reply_text(f"Шаблон '{set_data}' не найден.", 'Markdown')
        case "custom", 2:
            await update.message.reply_text("Загрузка кастомных шаблонов пока что не реализована.", 'Markdown')
            # chat.template = "custom"
            # chat.use_custom_template = True
        case _:
            await update.message.reply_text("Недопустимая команда.", "Markdown")


async def handle_private_messages(update, cmd, setts):
    match cmd:
        case "/start":
            await update.message.reply_text("/help")
        case "/help":
            uid = update.message.from_user.id
            await update.message.reply_text(
                help_msg.format("") if not uid in config.admins else help_msg.format(help_msg_admin),
                parse_mode='Markdown', disable_web_page_preview=True
            )
        case "/set_save_path":
            if not update.message.from_user.id in config.admins:
                await update.message.reply_text("Ты не админ")
                return
            if not setts:
                await update.message.reply_text(
                    f"Укажите путь для сохранения файлов: `/set_save_path <path>`\nTекущий путь: `{config.save_path}`",
                    parse_mode='Markdown')
                return
            old_path = config.config_file['save_path']
            try:
                config.config_file['save_path'] = setts
                if not os.path.exists(config.config_file['save_path']):
                    os.makedirs(config.config_file['save_path'])
                await update.message.reply_text(f"Путь для сохранения файлов изменен с `{old_path}` на `{setts}`",
                                                parse_mode='Markdown')
            except Exception as e:
                await update.message.reply_text(f"Ошибка при изменении пути: {e}")
                config.config_file['save_path'] = old_path
            config.save()
        case "/reload":
            if not update.message.from_user.id in config.admins:
                await update.message.reply_text("Ты не админ")
                return
            await update.message.reply_text(f"Chats Store:\n  {config.reload_chats()}")
            await update.message.reply_text(f"Links:\n  {parser.reload()}")
            await update.message.reply_text(f"Templates:\n  {templator.reload()}")

# Функция для обработки ответов на сообщения
async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cmd = update.message.text.split(" ")
    if not cmd:
        return
    cmd, setts = cmd[0], " ".join(cmd[1:])
    if not cmd.startswith('/'):
        return
    cmd = cmd.replace(f"@{username}", "")
    print(f"Команда: {cmd!r}; Аргументы: {setts!r}")
    if update.message.chat.type == 'private':
        await handle_private_messages(update, cmd, setts)

    match cmd:
        case "/auto":
            await handle_auto(update, context)
        case "/file":
            await handle_file(update, context)
        case "/set":
            await handle_settings(update)
            config.save_chats()
        case "/template":
            await handle_template(update)
            config.save_chats()
        case "/settings":
            chat = config.get_chat(update.message.chat.id)
            s = (
                f"**Настройки чата #`{update.message.chat_id}`**:\n"
                f" Форма обучения: `{('очное' if chat.ofo else 'очно-заочное/заочное') if chat.find else "не установлено"}`\n"
                f" URL страницы с расписанием: `{chat.url or "не установлено"}`\n"
                f" Строка для поиска файла: `{chat.find or "не установлено"}`\n"
                f" Название листа в файле: `{chat.sheet_name or "не установлено"}`\n"
                f" Шаблон вывода расписания: `{chat.template if not chat.use_custom_template else "кастомный"}`"
            )
            if not chat.ofo:
                s += ("\n\n**Дополнительно**:\n"
                      f" Ссылок в базе: `{len(parser.links)}`")
            if update.message.chat.type == 'private' and update.message.from_user.id in config.admins:
                s += ("\n\n**Админские настройки**:\n"
                      f" Путь для сохранения файлов: `{config.save_path}`")
            await update.message.reply_text(s, parse_mode='Markdown')
            if chat.use_custom_template:
                document = InputFile(json.dumps(chat.custom_template), "custom_template.json")
                await update.message.reply_document(document)

def main() -> None:
    global username
    # Создаем приложение
    application = Application.builder().token(config.token).build()

    # Регистрация обработчиков
    application.add_handler(MessageHandler(filters.TEXT & filters.REPLY, handle_messages))
    application.add_handler(MessageHandler(filters.TEXT, handle_messages))
    username = loop.run_until_complete(application.bot.get_me()).username
    print(f"Запустился. @{username}")

    # Запускаем бота
    application.run_polling()


if __name__ == '__main__':
    main()
