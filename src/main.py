import asyncio
import os
import traceback
from pathlib import Path

from telegram import Update, LinkPreviewOptions
from telegram.ext import Application, MessageHandler, filters, ContextTypes

from core import download_file, parse_xls, render_data, Config
from core.parser import links

# /set find 1 курс ОЗФО
# /set sheet 1к Прикладная математика

username = ""

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

config = Config("config.json", "chats.json")

async def render_and_send(update: Update, context: ContextTypes.DEFAULT_TYPE, file: Path, even_week):
    try:
        chat_id = update.effective_chat.id
        data = parse_xls(file, config.get(chat_id).sheet_name, even_week)
        if not data:
            await update.message.reply_text('Ошибка при обработке файла.')
            return
        if isinstance(data, str):
            raise Exception(data)
        text, parse_mode = render_data(data, "офо" in file.name.lower())
        # print(text)
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
        if config.get(update.message.chat.id).ofo:
            even_week = not "1" in update.message.text
        await render_and_send(update, context, file_path, even_week)
    else:
        await update.message.reply_text('Пожалуйста, ответьте на сообщение с документом.')

async def handle_auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not config.get(update.effective_chat.id).ready():
        await update.message.reply_text("Настройки не установлены.")
        return
    if config.get(update.effective_chat.id).ofo:
        await update.message.reply_text("Для ОФО нет поддержки так как админу лень делать поддержку 2х групп.\n"
                                        "Админ: @id0124\n"
                                        "Ссылка на проект для тех, кто хочет что-то изменить: [github](https://github.com/SantaSpeen/fa-bot)",
                                        parse_mode='Markdown', link_preview_options=LinkPreviewOptions(True))
        return
    mid = await update.message.reply_text("Поиск файла на сайте универа..", parse_mode='Markdown')
    chat_id = update.effective_chat.id
    chat_info = config.get(chat_id)
    even_week = None
    if chat_info.ofo:
        even_week = not "1" in update.message.text
    file_path = download_file(chat_info.url, chat_info.find, config.save_path, even_week)
    if not file_path:
        await context.bot.editMessageText('Ошибка при загрузке файла.', mid.chat_id, mid.message_id, parse_mode='Markdown')
        return
    # изменить сообщение mid
    s = f'Документ сохранен: `{file_path.name}`.\nОбработка файла...'
    await context.bot.editMessageText(s, mid.chat_id, mid.message_id, parse_mode='Markdown')
    await render_and_send(update, context, file_path, even_week)

allow_set_cmds = ("find", "sheet", "url")

async def handle_settings(update: Update):
    cmd = update.message.text.split(" ")
    cmd, setts = cmd[0], " ".join(cmd[1:])
    if not setts:
        await update.message.reply_text(
            "Ипользуйте команду в формате `/set <команда> <значение>`\n"
            f"Доступные команды: `{'`, `'.join(allow_set_cmds)}`", parse_mode='Markdown')
        return
    set_cmd, set_data = setts.split(" ", 1)
    if set_cmd not in allow_set_cmds:
        await update.message.reply_text(f"Недопустимая команда: `{set_cmd}`")
        return
    if not set_data:
        await update.message.reply_text(f"Укажите значение для установки: `/set {set_cmd} <значение>`")
        return
    chat_info = config.get(update.message.chat.id)
    match set_cmd:
        case "url":
            chat_info.url = set_data
            await update.message.reply_text(f"URL страницы с расписанием изменен на `{set_data}`", parse_mode='Markdown')
        case "find":
            if not chat_info.check_find(set_data):
                await update.message.reply_text(f"Недопустимое значение: `{set_data}`", parse_mode='Markdown')
                return
            chat_info.find = set_data
            await update.message.reply_text(f"Строка для поиска файла изменена на `{set_data}`", parse_mode='Markdown')
        case "sheet":
            if not chat_info.check_sheet(set_data):
                await update.message.reply_text(f"Недопустимое значение: `{set_data}`", parse_mode='Markdown')
                return
            chat_info.sheet_name = chat_info.fix_sheet(set_data)
            await update.message.reply_text(f"Название листа в файле с расписанием изменено на `{set_data}`. "
                                            f"{"Чётность недели убрана." if chat_info.sheet_name != set_data else ""}", parse_mode='Markdown')
    config.save()

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
        match cmd:
            case "/start":
                await update.message.reply_text("/help")
            case "/help":
                await update.message.reply_text(
                    "Доступные команды:\n"
                    "/auto - автоматический поиск и обработка файла\n"
                    "/file - обработка файла из ответа на сообщение\n"
                    "/settings - Настройки чата\n"
                    "Команды для настройки:\n"
                    "(Для каждого чата настраивается отдельно)\n"
                    "`/set <команда> <значение>`; Доступные команды:\n"
                    "  `url` - установить URL страницы с расписанием\n"
                    "  `find` - установить строку для поиска файла\n"
                    "  `sheet` - установить название листа в файле с расписанием\n",
                    parse_mode='Markdown'
                )
            case "/set_save_path":
                if not update.message.from_user.id in config.admins:
                    await update.message.reply_text("Ты не админ")
                    return
                if not setts:
                    await update.message.reply_text(f"Укажите путь для сохранения файлов: `/set_save_path <path>`\nTекущий путь: `{config.save_path}`", parse_mode='Markdown')
                    return
                old_path = config.global_config['save_path']
                try:
                    config.global_config['save_path'] = setts
                    if not os.path.exists(config.global_config['save_path']):
                        os.makedirs(config.global_config['save_path'])
                    await update.message.reply_text(f"Путь для сохранения файлов изменен с `{old_path}` на `{setts}`", parse_mode='Markdown')
                except Exception as e:
                    await update.message.reply_text(f"Ошибка при изменении пути: {e}")
                    config.global_config['save_path'] = old_path
                config.save()

    match cmd:
        case "/auto":
            await handle_auto(update, context)
        case "/file":
            await handle_file(update, context)
        case "/set":
            await handle_settings(update)
        case "/settings":
            chat_info = config.get(update.message.chat.id)
            if not chat_info.ready():
                await update.message.reply_text("Настройки не установлены.")
                return
            s = (
                "**Настройки чата**:\n"
                f" Форма обучения: `{'очное' if chat_info.ofo else 'очно-заочное/заочное'}`\n"
                f" URL страницы с расписанием: `{chat_info.url}`\n"
                f" Строка для поиска файла: `{chat_info.find}`\n"
                f" Название листа в файле: `{chat_info.sheet_name}`"
            )
            if not chat_info.ofo:
                s += ("\n\n**Дополнительно**:\n"
                      f" Ссылок на пары в базе: `{len(links)}`")
            if update.message.chat.type == 'private' and update.message.from_user.id in config.admins:
                s += ("\n\n**Админские настройки**:\n"
                      f" Путь для сохранения файлов: `{config.save_path}`")
            await update.message.reply_text(s, parse_mode='Markdown')

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
