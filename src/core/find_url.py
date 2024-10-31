import os
import urllib.parse

import requests
from bs4 import BeautifulSoup

def download_file(url, find):
    response = requests.get(url)
    if response.status_code == 200:
        # Парсим HTML-код страницы
        soup = BeautifulSoup(response.text, 'html.parser')

        # Ищем ссылку на файл с расписанием
        anchors = soup.find_all('a')
        link = [urllib.parse.unquote(a.get('href')) for a in anchors if
                a.get('href') and a.get("href").endswith(".xls") and find in a.text]

        if link:
            # Получаем полный URL файла
            file_url = "http://www.fa.ru" + link[0]
            file_name = os.path.basename(link[0]).replace("'","").replace(" ", "_")
            file_path = f"data/{file_name}"

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
