import os

from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

from core import download_file, parse_xls, render_data
from core.parser import links

# URL страницы с расписанием
url = "http://www.fa.ru/fil/krasnodar/student/Pages/schedule.aspx"
# Строка, которая должна содержаться в названии файла с расписанием
find = "1 курс ОЗФО"
# Название листа в файле с расписанием
sheet_name = "1к Прикладная математика"

# Замените на ваш токен
TELEGRAM_TOKEN = '5162929509:AAHtW8PFvwdcGfx7wH4bKU-bu_b2tvNok3g'
FILE_SAVE_PATH = 'data/'  # Папка для сохранения файлов

# Создадим папку, если она не существует
if not os.path.exists(FILE_SAVE_PATH):
    os.makedirs(FILE_SAVE_PATH)

async def render_and_send_data(update: Update, context: ContextTypes.DEFAULT_TYPE, file):
    try:
        chat_id = update.effective_chat.id  # Получение ID чата, откуда пришла команда
        data = parse_xls(file, sheet_name)
        if not data:
            await update.message.reply_text('Ошибка при обработке файла.')
            return
        await context.bot.send_message(chat_id=chat_id, text=render_data(data), parse_mode='HTML')
    except Exception as e:
        print(e)
        await update.message.reply_text(f'Ошибка при обработке файла: {e}')


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

        # Укажите путь для сохранения
        file_path = os.path.join(FILE_SAVE_PATH, filename)
        if os.path.exists(file_path):
            print(f"Файл '{filename}' уже существует.")
        else:
            await new_file.download_to_drive(file_path)
            print(f"Файл '{filename}' успешно сохранен!")

        s = f'Документ сохранен: `{file_path.replace(FILE_SAVE_PATH, "")}`.\nОбработка файла...'
        await context.bot.editMessageText(s, mid.chat_id, mid.message_id, parse_mode='Markdown')
        await render_and_send_data(update, context, file_path)
    else:
        await update.message.reply_text('Пожалуйста, ответьте на сообщение с документом.')

async def handle_auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mid = await update.message.reply_text("Поиск файла на сайте универа..", parse_mode='Markdown')
    file_path = download_file(url, find)
    if not file_path:
        await context.bot.editMessageText('Ошибка при загрузке файла.', mid.chat_id, mid.message_id, parse_mode='Markdown')
        return
    # изменить сообщение mid
    s = f'Документ сохранен: `{file_path.replace(FILE_SAVE_PATH, "").replace("'", "").replace(" ", "_")}`.\nОбработка файла...'
    await context.bot.editMessageText(s, mid.chat_id, mid.message_id, parse_mode='Markdown')
    await render_and_send_data(update, context, file_path)

# Функция для обработки ответов на сообщения
async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.message.text
    if not msg.startswith('/'):
        return
    match msg:
        case "/start":
            await update.message.reply_text("Привет! Я бот.")
        case "/auto":
            await handle_auto(update, context)
        case "/file":
            await handle_file(update, context)
        case "/info":
            await update.message.reply_text(
                "Информация о боте: \n"
                f"Фамилий в базе: `{len(links)}`\n"
                f"Ссылка с расписанием: '`{url}`'\n"
                f"Строка для поиска файла: '`{find}`'\n"
                f"Название листа в `.xls` файле: '`{sheet_name}`'\n"
                f"Админ: `есть`",
                parse_mode='Markdown'
            )

def main() -> None:
    # Создаем приложение
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Регистрация обработчиков
    application.add_handler(MessageHandler(filters.TEXT & filters.REPLY, handle_messages))
    application.add_handler(MessageHandler(filters.TEXT, handle_messages))

    # Запускаем бота
    application.run_polling()


if __name__ == '__main__':
    main()
