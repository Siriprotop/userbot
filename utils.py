import json
import requests

user_data = {}

def save_user_data():
    with open('users.json', 'w', encoding='utf-8') as file:
        json.dump(user_data, file, ensure_ascii=False)

def upload_image_to_imgur(image_path, client_id):
    url = "https://api.imgur.com/3/image"
    headers = {"Authorization": f"Client-ID {client_id}"}
    with open(image_path, "rb") as image:
        img = image.read()
    response = requests.post(url, headers=headers, files={"image": img})
    data = response.json()
    if response.status_code == 200:
        return data["data"]["link"]
    else:
        print(f"Ошибка загрузки изображения: {data}")
        return None
