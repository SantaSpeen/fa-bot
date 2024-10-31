import json

import pandas as pd

# Настройки
row_start = 13 # Номер строки с которой начинаются данные
row_end = 93  # Номер строки на которой заканчиваются данные

col_week = 0  # A Номер столбца с неделей
row_week = 8  # Номер строки с неделей

col_date = 0  # A Номер столбца с датой
col_num = 1  # B Номер столбца с номером пары
col_time = 3  # D Номер столбца с временем
col_name = 5  # E Номер столбца с названием предмета именем
offset_teacher = 1  # через сколько после col_name будет имя лектора
col_aud = 8 # I Номер столбца с аудиторией

len_day = 16 # Длина дня в строках
len_week = 5 # Длина недели в днях

# список дней недели в строках
week = [((row_start + len_day * i), row_start + len_day * (i + 1)) for i in range(len_week)]
with open("core/links.json", "r", encoding="utf-8") as f:
    links = json.load(f)

def say_nani_to_nan(x):
    if pd.isna(x):
        return None
    return x

def parse_xls(file_path, sheet_name):
    # Загружаем данные из .xls в DataFrame
    df = pd.read_excel(file_path, sheet_name=sheet_name)

    data = [{"date": None, "lessons": [{"name": None, "teacher": None, "time": None, "place": None, "link": None} for _ in range(8)]} for _ in range(len_week)]

    # Отбираем нужные строки
    for j, (start_day, end_day) in enumerate(week):
        c = 0  # class
        o = 0  # offset
        for i in range(start_day, end_day):
            if o > 1:
                o = 0
            date = df.iloc[i, col_date]
            if o == 0:
                if not pd.isna(date):
                    data[j]['date'] = date
                num = df.iloc[i, col_num]
                if not pd.isna(num):
                    c = int(num) - 1
                data[j]['lessons'][c]['name'] = say_nani_to_nan(df.iloc[i, col_name])
                data[j]['lessons'][c]['time'] = say_nani_to_nan(df.iloc[i, col_time])
                data[j]['lessons'][c]['place'] = say_nani_to_nan(df.iloc[i, col_aud])
            if o == offset_teacher:
                data[j]['lessons'][c]['teacher'] = say_nani_to_nan(df.iloc[i, col_name])
                if data[j]['lessons'][c]['teacher'] is not None:
                    data[j]['lessons'][c]['link'] = links.get(data[j]['lessons'][c]['teacher'].split(" ")[0].lower(), None)
            o += 1
    data.append(df.iloc[row_week, col_week])

    return data