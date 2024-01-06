import os

# Список названий файлов
file_names = [
    "Kyiv.json",
    "Kharkiv.json",
    "Odesa.json",
    "Lviv.json",
    "Dnipro.json",
    "Zaporizhzhia.json",
    "Mykolaiv.json",
    "Ivano-Frankivsk.json",
    "Kryvyi Rih.json",
    "Rivne.json",
    "Chernivtsi.json",
    "Cherkasy.json",
    "Sumy.json",
    "Zhytomyr.json",
    "Kropyvnytskyi.json",
    "Ternopil.json",
    "Lutsk.json",
    "Khmelnytskyi.json",
    "Poltava.json",
    "Uzhhorod.json",
    "Chernihiv.json",
    "Vinnytsia.json",
    "Kherson.json"
]

# Получить путь к папке, где находится этот скрипт
script_folder = os.path.dirname(os.path.abspath(__file__))

# Создание файлов
for file_name in file_names:
    file_path = os.path.join(script_folder, file_name)
    with open(file_path, 'w') as file:
        # Можно добавить начальные данные в каждый файл, если это необходимо
        file.write('{"announcements": []}')

