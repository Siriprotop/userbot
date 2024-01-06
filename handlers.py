from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler
import datetime
from utils import save_user_data, upload_image_to_imgur, user_data  # Make sure utils.py is in the same directory
from config import MODERATOR_IDS
from constants import EXACT_ADDRESS, DETAILS, PHOTO, EDIT_ADDRESS, CHOOSE_CITY, BROADCAST_MSG
import json

# Handlers
def broadcast_moderator(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    if user_id in MODERATOR_IDS:
        keyboard = [
            [InlineKeyboardButton("Всем городам", callback_data='broadcast_all')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text("Выберите опцию рассылки:", reply_markup=reply_markup)
        return CHOOSE_CITY
    else:
        update.message.reply_text("У вас нет прав на использование этой команды.")
        return ConversationHandler.END

def broadcast_to_city(update: Update, context: CallbackContext) -> int:
    message = update.message.text
    city_file = context.user_data.get('city_file')

    try:
        with open(city_file, 'r', encoding='utf-8') as file:
            content = json.load(file)

        if isinstance(content, dict):
            announcements = [content]
        elif isinstance(content, list):
            announcements = content
        else:
            raise ValueError("Unexpected data format in the JSON file.")

        for announcement in announcements:
            try:
                user_id = announcement['publishedUser']
                try:
                    sent_message = context.bot.send_message(chat_id=user_id, text=message)
                    if sent_message:
                        print(f'Successsfulled sent to {user_id}')
                    else:
                        print(f'Error')
                except Exception as err:
                    print(err)

            except Exception as e:
                print(f"Ошибка при отправке сообщения: {e}")
                continue

        update.message.reply_text(f"Сообщение отправлено пользователям города, указанного в файле {city_file}.")

    except FileNotFoundError:
        update.message.reply_text(f"Файл {city_file} не найден.")
    except json.JSONDecodeError as e:
        update.message.reply_text(f"Ошибка в формате файла {city_file}: {e}")
    except ValueError as e:
        update.message.reply_text(str(e))

    return ConversationHandler.END

def choose_city(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    chosen_city = query.data

    city_files = {
        "Київ": "Kyiv.json",
        "Харків": "Kharkiv.json",
        "Одеса": "Odesa.json",
        "Львів": "Lviv.json",
        "Дніпро": "Dnipro.json",
        "Запоріжжя": "Zaporizhzhia.json",
        "Миколаїв": "Mykolaiv.json",
        "Івано-Франківськ": "Ivano-Frankivsk.json",
        "Кривий Ріг": "Kryvyi Rih.json",
        "Рівне": "Rivne.json",
        "Чернівці": "Chernivtsi.json",
        "Черкаси": "Cherkasy.json",
        "Суми": "Sumy.json",
        "Житомир": "Zhytomyr.json",
        "Кропивницький": "Kropyvnytskyi.json",
        "Тернопіль": "Ternopil.json",
        "Луцьк": "Lutsk.json",
        "Хмельницький": "Khmelnytskyi.json",
        "Полтава": "Poltava.json",
        "Ужгород": "Uzhhorod.json",
        "Чернігів": "Chernihiv.json",
        "Вінниця": "Vinnytsia.json",
        "Херсон": "Kherson.json",
    }

    if chosen_city == 'broadcast_all':
        query.edit_message_text(text="Введите сообщение для рассылки:")
        return BROADCAST_MSG
    elif chosen_city in city_files:
        context.user_data['city_file'] = city_files[chosen_city]
        query.edit_message_text(text=f"Введите сообщение для рассылки пользователям из {chosen_city}:")
        return BROADCAST_MSG

    query.edit_message_text(text="Некорректный выбор города.")
    return ConversationHandler.END

def start(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id
    user_data[user_id] = {}
    update.message.reply_text(
        "Дякую що підписалися на робота WTU. Ми будемо повідомляти Вас про актуальні адреси WTU.\n\n"
    )

def city(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id
    cities = [
        "Київ", "Харків", "Одеса", "Львів", "Дніпро", "Запоріжжя", "Миколаїв",
        "Івано-Франківськ", "Кривий Ріг", "Рівне", "Чернівці", "Черкаси", "Суми", 
        "Житомир", "Кропивницький", "Тернопіль", "Луцьк", "Хмельницький", "Полтава",
        "Ужгород", "Чернігів", "Вінниця", "Херсон"
    ]
    keyboard = [[InlineKeyboardButton(city, callback_data=city)] for city in cities]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Вибери місто:', reply_markup=reply_markup)

    save_user_data()

def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    user_id = query.message.chat_id
    if user_id not in user_data:
        user_data[user_id] = {}
    if query.data.startswith('no_'):
        user_id_to_delete = int(query.data[3:])
        user_data.pop(user_id_to_delete, None)
        save_user_data()
        
        try:
            query.edit_message_text(text="Отклонено")
            return
        except Exception as e:
            print(e)
            return
    elif query.data.startswith('yr'):
        user_id_to_edit = int(query.data[3:])

        if user_id_to_edit in user_data:
            context.user_data['EDIT_USER_ID'] = user_id_to_edit
            user_data[user_id]['EDIT_USER_ID'] = user_id_to_edit
            user_data[user_id]['is_editing'] = True
            update.effective_message.reply_text("<b>1) Введите точный адрес (обязательно)</b>\nЧем точнее будет адрес, тем лучше.\nНапр: Богдана Хмельницкого, 33.", parse_mode='HTML')
            return EXACT_ADDRESS
        else:
            query.answer(text="Данные пользователя не найдены.")
            return
    elif query.data.startswith('yp'):
        user_id_to_edit = int(query.data[3:])
        if user_id_to_edit in user_data:
            city_to_check = user_data[user_id_to_edit]['CITY']
            address = user_data[user_id_to_edit]['EXACT_ADDRESS']
            details = user_data[user_id_to_edit].get('DETAILS', '')
            photo = user_data[user_id_to_edit].get('PHOTO', '')
            date_time = user_data[user_id_to_edit].get('DATE_TIME', '')

            for uid, data in user_data.items():
                if data.get('CITY') == city_to_check:
                    try:
                        context.bot.send_message(
                            chat_id=uid,
                            text=f"{address}\n{details}\n{photo}\n{date_time}"
                        )
                        city_files = {
                            "Київ": "Kyiv.json",
                            "Харків": "Kharkiv.json",
                            "Одеса": "Odesa.json",
                            "Львів": "Lviv.json",
                            "Дніпро": "Dnipro.json",
                            "Запоріжжя": "Zaporizhzhia.json",
                            "Миколаїв": "Mykolaiv.json",
                            "Івано-Франківськ": "Ivano-Frankivsk.json",
                            "Кривий Ріг": "Kryvyi Rih.json",
                            "Рівне": "Rivne.json",
                            "Чернівці": "Chernivtsi.json",
                            "Черкаси": "Cherkasy.json",
                            "Суми": "Sumy.json",
                            "Житомир": "Zhytomyr.json",
                            "Кропивницький": "Kropyvnytskyi.json",
                            "Тернопіль": "Ternopil.json",
                            "Луцьк": "Lutsk.json",
                            "Хмельницький": "Khmelnytskyi.json",
                            "Полтава": "Poltava.json",
                            "Ужгород": "Uzhhorod.json",
                            "Чернігів": "Chernihiv.json",
                            "Вінниця": "Vinnytsia.json",
                            "Херсон": "Kherson.json",
                        }
                        city_file = city_files.get(city_to_check, None)

                        if city_file:
                            try:
                                with open(city_file, 'r', encoding='utf-8') as file:
                                    data = json.load(file)

                                announcement = {
                                    "address": address,
                                    "comment": details,
                                    "photourl": photo,
                                    "publishedDate": date_time,
                                    "publishedUser": user_id_to_edit
                                }

                                with open(city_file, 'w', encoding='utf-8') as file:
                                    json.dump(announcement, file, ensure_ascii=False)

                            except Exception as e:
                                print(f"Не удалось обновить файл {city_file}: {e}")

                    except Exception as e:
                        print(f"Не удалось отправить сообщение пользователю {uid}: {e}")

            else:
                query.answer(text="Данные для рассылки не найдены.")
        
    else:
        user_data[user_id]['CITY'] = query.data
        save_user_data()
        query.edit_message_text(text=f"Вибране місто: {query.data}")

        reply_keyboard = [
            ["Повідомити нову адресу"]
            # ["Відкрити карту адрес"],
        ]
        if user_id in MODERATOR_IDS:
            reply_keyboard.append(["Рассылка модератором"])
        update.effective_message.reply_text(
            'Оберіть опцію:',
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        )

def new_address(update: Update, context: CallbackContext) -> int:
    user_id = update.message.chat_id
    update.message.reply_text("<b>1) Введите точный адрес (обязательно)</b>\nЧем точнее будет адрес, тем лучше.\nНапр: Богдана Хмельницкого, 33.", parse_mode='HTML')
    return EXACT_ADDRESS

def exact_address(update: Update, context: CallbackContext) -> int:
    text = update.message.text
    user_id = update.message.chat_id
    
    if 'EDIT_USER_ID' in context.user_data:
        user_id_to_edit = context.user_data['EDIT_USER_ID']
        print(f'USER ID TO EDIT IN EXACT {user_id_to_edit}')
        user_data[user_id_to_edit]['EXACT_ADDRESS'] = text
        save_user_data()
        update.message.reply_text("<b>2) Деталі місця (необязательно)</b>\nУкажите где вы это заметили\nНапр: Рядом красная вывеска, и магазин Море Пива", parse_mode='HTML')
        return DETAILS
    else:
        user_data[user_id]['EXACT_ADDRESS'] = text
        update.message.reply_text("<b>2) Деталі місця (необязательно)</b>\nУкажите где вы это заметили\nНапр: Рядом красная вывеска, и магазин Море Пива", parse_mode='HTML')
        return DETAILS



def details(update: Update, context: CallbackContext) -> int:
    text = update.message.text
    user_id = update.message.chat_id
    if 'EDIT_USER_ID' in context.user_data:
        user_id_to_edit = context.user_data['EDIT_USER_ID']
        user_data[user_id_to_edit]['DETAILS'] = text
        save_user_data()
        update.message.reply_text('<b>3) Фото місця (необязательно)</b>', parse_mode='HTML')
        return PHOTO
    user_data[user_id]['DETAILS'] = text
    update.message.reply_text("<b>3) Фото місця (необязательно)</b>", parse_mode='HTML')
    return PHOTO



def updaterPhoto(update: Update, context: CallbackContext) -> int:
    user_id = update.message.chat_id
    photo_file = update.message.photo[-1].get_file()
    photo_path = f'user_{user_id}_photo.jpg'
    photo_file.download(photo_path)
    imgur_url = upload_image_to_imgur(photo_path, "a4d7dd18d36705f")
    user_id_to_edit = context.user_data['EDIT_USER_ID']
    print(imgur_url)
    if imgur_url:
        user_data[user_id_to_edit]['PHOTO'] = imgur_url
        save_user_data()
    else:
        update.message.reply_text("Не удалось загрузить фото.")

    if user_id_to_edit in user_data:
        city_to_check = user_data[user_id_to_edit]['CITY']
        address = user_data[user_id_to_edit]['EXACT_ADDRESS']
        details = user_data[user_id_to_edit].get('DETAILS', '')
        photo = user_data[user_id_to_edit].get('PHOTO', '')
        date_time = user_data[user_id_to_edit].get('DATE_TIME', '')
        for uid, data in user_data.items():
            if data.get('CITY') == city_to_check:
                try:
                    context.bot.send_message(
                        chat_id=uid,
                        text=f"{address}\n{details}\n<b>{photo}</b>\n{date_time}",
                        parse_mode='HTML'
                    )
                except Exception as e:
                    print(f"Не удалось отправить сообщение пользователю {uid}: {e}")
    
    del user_data[user_id]['EDIT_USER_ID']
    return ConversationHandler.END

def photo(update: Update, context: CallbackContext) -> int:
    user_id = update.message.chat_id
    photo_file = update.message.photo[-1].get_file()
    photo_path = f'user_{user_id}_photo.jpg'
    photo_file.download(photo_path)
    imgur_url = upload_image_to_imgur(photo_path, "a4d7dd18d36705f")
    print(imgur_url)
    if imgur_url:
        user_data[user_id]['PHOTO'] = imgur_url
    else:
        update.message.reply_text("Не удалось загрузить фото.")
    user_data[user_id]['DATE_TIME'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_user_data()
    update.message.reply_text('Дякуємо, що залишили нову адресу. Ваша інформація буде перебувати на перевірці, і незабаром буде опублікована.', parse_mode='HTML')
    
    message_text = (
        "Опублікувати наступну адресу?\n"
        f"{user_data[user_id]['EXACT_ADDRESS']}\n"
        f"{user_data[user_id]['DETAILS']}\n"
        f"{imgur_url}\n"
        f"{user_data[user_id]['DATE_TIME']}\n"
        f"{user_id}\n"
    )
    keyboard = [
        [
            InlineKeyboardButton("N", callback_data=f"no_{user_id}"),
            InlineKeyboardButton("YR", callback_data=f"yr_{user_id}"),
            InlineKeyboardButton("YP", callback_data=f"yp_{user_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(
        chat_id=6964683351,
        text=message_text,
        reply_markup=reply_markup
    )

    return ConversationHandler.END

def skip_photo(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("Фото пропущено.")
    save_user_data()
    return ConversationHandler.END

def cancel(update: Update, context: CallbackContext) -> int:
    update.message.reply_text('Отменено.', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def edit_address(update: Update, context: CallbackContext) -> int:
    user_id = update.message.chat_id
    user_id_to_edit = user_data[user_id]['EDIT_USER_ID']
    if user_id_to_edit in user_data:
        user_data[user_id]['is_editing'] = True
        update.message.reply_text("Введите новый точный адрес (обязательно):")
        return EXACT_ADDRESS
    else:
        update.message.reply_text("Пользователь не найден.")
        return ConversationHandler.END