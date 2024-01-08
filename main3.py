import json
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext, MessageHandler, Filters, ConversationHandler
import requests
import uuid
import telegram
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

city_channels = {
    "Київ": '-1002009215054',
    "Харків": '-1001990345559',
    "Одеса": '-1002018743530',
    "Львів": '-1002011256616',
    "Дніпро": '-1002002447389',
    "Херсон": '-1002074975452',
    "Вінниця": '-1002039986567',
    "Чернігів": '-1002036937534',
    "Ужгород": '-1002004066415',
    "Полтава": '-1002141539514',
    "Хмельницький": '-1001777761375',
    "Луцьк": '-1002009986196',
    "Тернопіль": '-1002102395207',
    "Кропивницький": '-1002131249827',
    "Житомир": '-1002016456677',
    "Суми": '-1002105965919',
    "Черкаси": '-1002077464146',
    "Чернівці": '-1002035929578',
    "Рівне": '-1002101920363',
    "Кривий Ріг": '-1002024876100',
    "Івано-Франківськ": '-1002077710288',
    "Миколаїв": '-1002005889645',
    "Запоріжжя": '-1002062185937'
}
EXACT_ADDRESS, DETAILS, PHOTO, EDIT_ADDRESS = range(4)

user_data = {}
moderator_ids = [5873932146]

ukrainian_months = {
    1: "січня", 2: "лютого", 3: "березня", 4: "квітня",
    5: "травня", 6: "червня", 7: "липня", 8: "серпня",
    9: "вересня", 10: "жовтня", 11: "листопада", 12: "грудня"
}


CHOOSE_city, BROADCAST_MSG, BROADCAST_ALL = range(5, 8)


def error_handler(update, context):
    """Логируем ошибки, вызванные обновлениями."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)

# Initialize this somewhere accessible in your code
published_posts = set()
def format_message(address, details, photo, date_time):
    message_parts = [address, details if details.strip() != '' else None, photo if photo.strip() != '' else None, date_time]
    return "\n".join(filter(None, message_parts))

def format_without_photo(address, details, date_time):
    message_parts = [address, details if details.strip() != '' else None, date_time]
    return "\n".join(filter(None, message_parts))



def save_user_data(user_id):
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
    print("Attempting to save data for user:", user_id)  # Debug print

    city = user_data.get(user_id, {}).get('city')
    print("City is:", city)  # Debug print

    if city and city in city_files:
        file_name = city_files[city]
        print("Saving to file:", file_name)

        try:
            with open(file_name, 'r+', encoding='utf-8') as file:
                try:
                    # Try to load the existing data
                    data = json.load(file)
                except json.decoder.JSONDecodeError:
                    # If JSON is empty or broken, start fresh
                    print(f"JSONDecodeError encountered. Initializing {file_name} as empty.")
                    data = {}

                # Update data with the new user information
                data[str(user_id)] = user_data[user_id]
                file.seek(0)  # Go back to the start of the file
                json.dump(data, file, ensure_ascii=False)
                file.truncate()  # Remove leftover content

        except FileNotFoundError:
            # If the file doesn't exist, create a new one and write the data
            with open(file_name, 'w', encoding='utf-8') as file:
                json.dump({str(user_id): user_data[user_id]}, file, ensure_ascii=False)


def broadcast(update: Update, context: CallbackContext, user_ids) -> None:
    message = update.message
    if message.text:
        for user_id in user_ids:
            try:
                # Attempt to send the message
                context.bot.send_message(chat_id=user_id, text=message.text)
            except telegram.error.BadRequest as e:
                # Log the error and continue with the next user ID
                print(f"Failed to send message to {user_id}: {e}")
    elif message.photo:
        # Send the highest quality photo
        photo = message.photo[-1].file_id
        for user_id in user_ids:
            try:
                context.bot.send_photo(chat_id=user_id, photo=photo)
            except telegram.error.BadRequest as e:
                # Log the error and continue with the next user ID
                print(f"Failed to send message to {user_id}: {e}")
    elif message.document:
        # Send document
        document = message.document.file_id
        for user_id in user_ids:
            try:
                context.bot.send_document(chat_id=user_id, document=document)
            except telegram.error.BadRequest as e:
                # Log the error and continue with the next user ID
                print(f"Failed to send message to {user_id}: {e}")
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

def broadcast_moderator(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    if user_id in moderator_ids:
        keyboard = [
            [InlineKeyboardButton("Всем городам", callback_data='broadcast_all')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text("Выберите опцию рассылки:", reply_markup=reply_markup)
        return CHOOSE_city
    else:
        update.message.reply_text("У вас нет прав на использование этой команды.")
        return ConversationHandler.END

def broadcast_to_all_cities(update: Update, context: CallbackContext) -> int:
    message = update.message.text

    # Словарь каналов и их тегов

    # Проходим по всем каналам и отправляем сообщение
    for city, channel_username in city_channels.items():
        try:
            context.bot.send_message(chat_id=channel_username, text=message)
        except telegram.error.BadRequest as e:
            print(f"Failed to send message to {channel_username}: {e}")

    update.message.reply_text("Content sent to all city channels.")
    return ConversationHandler.END



def broadcast_to_city(update: Update, context: CallbackContext) -> int:
    message = update.message

    # Проверка на наличие текста в сообщении
    if message.text:
        content = message.text
    else:
        content = None

    # Проверка на наличие фото
    if message.photo:
        photo = message.photo[-1].file_id  # Берем последнее фото (самое большое)
    else:
        photo = None

    # Проверка на наличие документа
    if message.document:
        document = message.document.file_id
    else:
        document = None

    for city, channel_id in city_channels.items():
        try:
            if content and photo:
                # Отправка текста и фото
                context.bot.send_photo(chat_id=channel_id, photo=photo, caption=content)
            elif content:
                # Отправка только текста
                context.bot.send_message(chat_id=channel_id, text=content)
            elif photo:
                # Отправка только фото
                context.bot.send_photo(chat_id=channel_id, photo=photo)
            elif document:
                # Отправка только документа
                context.bot.send_document(chat_id=channel_id, document=document)
        except telegram.error.BadRequest as e:
            print(f"Failed to send message to channel {channel_id} for city {city}: {e}")

    update.message.reply_text("Content sent to all city channels.")
    return ConversationHandler.END



def choose_city(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    user_id = update.effective_user.id  # Get user_id from the effective user
    chosen_city = query.data
    if user_id not in user_data:
        user_data[user_id] = {}  # Initialize an empty dict for the user

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
        return BROADCAST_ALL
    elif chosen_city in city_files:
        # Now we're sure user_id is initialized, so we can safely assign city
        user_data[user_id]['city'] = chosen_city
        context.user_data['city_file'] = city_files[chosen_city]
        save_user_data(user_id)  # Save to the city-specific file
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

    city(update, context)

def city(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id
    cities = [
        "Київ", "Харків", "Одеса", "Львів", "Дніпро", "Запоріжжя", "Миколаїв",
        "Івано-Франківськ", "Кривий Ріг", "Рівне", "Чернівці", "Черкаси", "Суми",
        "Житомир", "Кропивницький", "Тернопіль", "Луцьк", "Хмельницький", "Полтава",
        "Ужгород", "Чернігів", "Вінниця", "Херсон"
    ]
    keyboard = [[InlineKeyboardButton(cities[i], callback_data=cities[i]),
                 InlineKeyboardButton(cities[i + 1], callback_data=cities[i + 1])]
                 for i in range(0, len(cities) - 1, 2)]
    if len(cities) % 2 != 0:
        keyboard.append([InlineKeyboardButton(cities[-1], callback_data=cities[-1])])

    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Вибери місто:', reply_markup=reply_markup)

def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    user_id = query.message.chat_id
    chosen_city = query.data
    
    if query.data == 'skip_photo':
        users_datas3 = {}
        if 'EDIT_USER_ID' in context.user_data:
            user_id_to_edit = context.user_data['EDIT_USER_ID']
            if user_id_to_edit in user_data:
                post_id = user_data[user_id_to_edit].get('POST_ID')
                published_posts.add(post_id) 
                city_to_check = user_data[user_id_to_edit]['city']
                address = user_data[user_id_to_edit]['EXACT_ADDRESS']
                details = user_data[user_id_to_edit].get('DETAILS', '')
                user_data[user_id_to_edit].pop('PHOTO', None)
                date_time = user_data[user_id_to_edit].get('DATE_TIME', '')

                city_channel = city_channels.get(city_to_check)
                if city_channel:
                    try:
                        context.bot.send_message(
                            chat_id=city_channel,
                            text=format_without_photo(address, details, date_time)
                        )
                        return ConversationHandler.END
                    except Exception as e:
                        print(f"Не удалось отправить сообщение в канал {city_channel}: {e}")
                        return ConversationHandler.END
                else:
                    query.answer(text="Канал для данного города не найден.")
                    return ConversationHandler.END
        print('GGG')
        query.message.reply_text("<b>Дякуємо, що залишили нову адресу. Ваша інформація буде перебувати на перевірці, і незабаром буде опублікована.</b>", parse_mode='HTML')
        now = datetime.datetime.now()
        month_name = ukrainian_months[now.month]  # Get Ukrainian month name
        formatted_date = now.strftime(f"%d {month_name}, %H:%M")  # Format the date
        user_data[user_id]['DATE_TIME'] = formatted_date
        save_user_data(user_id)  # Pass user_id to function
        if user_data[user_id]['DETAILS']:
            message_text = (
                "Опублікувати наступну адресу?\n"
                f"{user_data[user_id]['EXACT_ADDRESS']}\n"
                f"{user_data[user_id]['DETAILS']}\n"
                f"{user_data[user_id]['DATE_TIME']}\n"
                f"{user_data[user_id]['city']}\n"
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
                chat_id=5873932146,
                text=message_text,
                reply_markup=reply_markup
            )

            return ConversationHandler.END
        else:
            message_text = (
                "Опублікувати наступну адресу?\n"
                f"{user_data[user_id]['EXACT_ADDRESS']}\n"
                f"{user_data[user_id]['DATE_TIME']}\n"
                f"{user_data[user_id]['city']}\n"
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
                chat_id=5873932146,
                text=message_text,
                reply_markup=reply_markup
            )
            return ConversationHandler.END

    if query.data == 'skip_details':
        user_data[user_id]['DETAILS'] = ""
        keyboard = [
        [InlineKeyboardButton("Пропустити", callback_data='skip_photo')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.bot.send_message(chat_id=user_id, text="<b>3) Фото місця (необязательно)</b>", parse_mode='HTML', reply_markup=reply_markup)
        return PHOTO
    if user_id not in user_data:
        user_data[user_id] = {}
    if query.data.startswith('no_'):
        user_id_to_delete = int(query.data[3:])
        post_id = user_data[user_id_to_delete].get('POST_ID')
        query.edit_message_text(text="This post has already been published")

        # If the post is not published, then handle the rejection normally
        user_data.pop(user_id_to_delete, None)
        save_user_data(user_id_to_delete)
        
        try:
            query.edit_message_text(text="Отклонено")
            return ConversationHandler.END
        except Exception as e:
            print(e)
            return ConversationHandler.END

    elif query.data.startswith('yr'):
        user_id_to_edit = int(query.data[3:])

        if user_id_to_edit in user_data:
            post_id = user_data[user_id_to_edit].get('POST_ID')
            query.edit_message_text(text="This post has already been published.")
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
            post_id = user_data[user_id_to_edit].get('POST_ID')
            query.edit_message_text(post_id, 'This post has already been published')
            published_posts.add(post_id) 
            city_to_check = user_data[user_id_to_edit]['city']
            address = user_data[user_id_to_edit]['EXACT_ADDRESS']
            details = user_data[user_id_to_edit].get('DETAILS', '')
            photo = user_data[user_id_to_edit].get('PHOTO', '')
            date_time = user_data[user_id_to_edit].get('DATE_TIME', '')

            city_channel = city_channels.get(city_to_check)
            if city_channel:
                try:
                    context.bot.send_message(
                        chat_id=city_channel,
                        text=format_message(address, details, photo, date_time)
                    )
                except Exception as e:
                    print(f"Не удалось отправить сообщение в канал {city_channel}: {e}")
            else:
                query.answer(text="Канал для данного города не найден.")

            
    else:
        user_data[user_id]['city'] = query.data
        print("City set to:", user_data[user_id]['city'])  # Debug print
        save_user_data(user_id)
        query.edit_message_text(text=f"Вибране місто: {query.data}")

        reply_keyboard = [
            ["Повідомити нову адресу"],
            ["Відкрити карту адрес"],
        ]
        if user_id in moderator_ids:
            reply_keyboard.append(["Рассылка модератором"])
        update.effective_message.reply_text(
            'Оберіть опцію:',
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False, resize_keyboard=True)
        )

def new_address(update: Update, context: CallbackContext) -> int:
    user_id = update.message.chat_id
    update.message.reply_text("<b>1) Введите точный адрес (обязательно)</b>\nЧем точнее будет адрес, тем лучше.\nНапр: Богдана Хмельницкого, 33.", parse_mode='HTML')
    return EXACT_ADDRESS

def exact_address(update: Update, context: CallbackContext) -> int:
    text = update.message.text
    user_id = update.message.chat_id
    if user_id not in user_data:
        user_data[user_id] = {}
    keyboard = [
        [InlineKeyboardButton("Пропустити", callback_data='skip_details')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if 'EDIT_USER_ID' in context.user_data:
        user_id_to_edit = context.user_data['EDIT_USER_ID']
        print(f'USER ID TO EDIT IN EXACT {user_id_to_edit}')
        user_data[user_id_to_edit]['EXACT_ADDRESS'] = text
        save_user_data(user_id_to_edit)
        update.message.reply_text("<b>2) Деталі місця (необязательно)</b>\nУкажите где вы это заметили\nНапр: Рядом красная вывеска, и магазин Море Пива", reply_markup=reply_markup, parse_mode='HTML')
        return DETAILS
    else:
        user_data[user_id]['EXACT_ADDRESS'] = text
        update.message.reply_text("<b>2) Деталі місця (необязательно)</b>\nУкажите где вы это заметили\nНапр: Рядом красная вывеска, и магазин Море Пива", reply_markup=reply_markup, parse_mode='HTML')
        return DETAILS



def details(update: Update, context: CallbackContext) -> int:
    text = update.message.text
    user_id = update.message.chat_id
    if user_id not in user_data:
        user_data[user_id] = {}
    keyboard = [
        [InlineKeyboardButton("Пропустити", callback_data='skip_photo')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if 'EDIT_USER_ID' in context.user_data:
        user_id_to_edit = context.user_data['EDIT_USER_ID']
        user_data[user_id_to_edit]['DETAILS'] = text
        save_user_data(user_id_to_edit)
        update.message.reply_text('<b>3) Фото місця (необязательно)</b>', parse_mode='HTML', reply_markup=reply_markup)
        return PHOTO
    user_data[user_id]['DETAILS'] = text
    update.message.reply_text("<b>3) Фото місця (необязательно)</b>", parse_mode='HTML', reply_markup=reply_markup)
    return PHOTO



def updaterPhoto(update: Update, context: CallbackContext) -> int:
    user_id = update.message.chat_id
    user_id_to_edit = context.user_data.get('EDIT_USER_ID', user_id)  # getting the user id to edit

    if update.message.photo:
        photo_file = update.message.photo[-1].get_file()
        photo_path = f'user_{user_id}_photo.jpg'
        photo_file.download(photo_path)
        imgur_url = upload_image_to_imgur(photo_path, "a4d7dd18d36705f")

        if imgur_url:
            user_data[user_id_to_edit]['PHOTO'] = imgur_url
        else:
            update.message.reply_text("Не удалось загрузить фото.")

    now = datetime.datetime.now()
    month_name = ukrainian_months[now.month]
    formatted_date = now.strftime(f"%d {month_name}, %H:%M")
    user_data[user_id_to_edit]['DATE_TIME'] = formatted_date
    save_user_data(user_id_to_edit)
    if True:
        if user_id_to_edit in user_data:
            post_id = user_data[user_id_to_edit].get('POST_ID')
            published_posts.add(post_id) 
            print(published_posts)
            city_to_check = user_data[user_id_to_edit]['city']
            address = user_data[user_id_to_edit]['EXACT_ADDRESS']
            details = user_data[user_id_to_edit].get('DETAILS', '')
            photo = user_data[user_id_to_edit].get('PHOTO', '')
            date_time = user_data[user_id_to_edit].get('DATE_TIME', '')


            city_channel = city_channels.get(city_to_check)
            if city_channel:
                try:
                    context.bot.send_message(
                        chat_id=city_channel,
                        text=format_message(address, details, photo, date_time)
                    )
                    query.edit_message_text(text="This post has already been published.")
                except Exception as e:
                    print(f"Не удалось отправить сообщение в канал {city_channel}: {e}")
            else:
                query.answer(text="Канал для данного города не найден.")
    return ConversationHandler.END


def photo(update, context: CallbackContext) -> int:
    user_id = update.message.chat_id
    if user_id not in user_data:
        user_data[user_id] = {}
    # Check if the update message actually has a photo
    if update.message.photo:
        photo_file = update.message.photo[-1].get_file()
        photo_path = f'user_{user_id}_photo.jpg'
        photo_file.download(photo_path)
        imgur_url = upload_image_to_imgur(photo_path, "a4d7dd18d36705f")
        
        # Process the photo and update user data
        if imgur_url:
            user_data[user_id]['PHOTO'] = imgur_url
            photo_status = imgur_url  # Successfully uploaded photo URL
        else:
            user_data[user_id]['PHOTO'] = "Failed to upload photo"
            photo_status = "Не удалось загрузить фото."
            update.message.reply_text(photo_status)
    else:
        # If there's no photo, set a placeholder or skip the photo part
        photo_status = ""
    # Common details for both cases
    now = datetime.datetime.now()
    month_name = ukrainian_months[now.month]  # Ensure ukrainian_months dict is defined
    formatted_date = now.strftime(f"%d {month_name}, %H:%M")
    user_data[user_id]['DATE_TIME'] = formatted_date
    save_user_data(user_id)

    # Prepare the message text with or without the photo URL
    try:
        # Сначала соберите все части сообщения, проверяя наличие содержимого.
        address = user_data[user_id].get('EXACT_ADDRESS', '').strip()
        details = user_data[user_id].get('DETAILS', '').strip()
        city = user_data[user_id].get('city', '').strip()
        photo_status = user_data[user_id].get('PHOTO', '').strip()
        date_time = user_data[user_id].get('DATE_TIME', '').strip()
        user_id_str = str(user_id).strip()

        # Соберите список непустых строк.
        message_parts = [address, details if details else "", city, photo_status, date_time, user_id_str]

        # Объедините непустые строки, вставляя перенос строки между ними.
        message_text = "\n".join(part for part in message_parts if part)

        # Добавьте заголовок сообщения.
        message_text = "Опублікувати наступну адресу?\n" + message_text


        keyboard = [
            [InlineKeyboardButton("N", callback_data=f"no_{user_id}"),
            InlineKeyboardButton("YR", callback_data=f"yr_{user_id}"),
            InlineKeyboardButton("YP", callback_data=f"yp_{user_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text("<b>Дякуємо, що залишили нову адресу. Ваша інформація буде перебувати на перевірці, і незабаром буде опублікована.</b>", parse_mode='HTML')
        sent_message = context.bot.send_message(chat_id=5873932146, text=message_text, reply_markup=reply_markup)  # Change chat_id as needed
        user_data[user_id]['POST_ID'] = sent_message.message_id
    except Exception as e:
        print(e)

def broadcast_message(update: Update, context: CallbackContext) -> int:
    update.message.reply_text('https://www.google.com/maps/')
    return ConversationHandler.END
def skip_photo(update: Update, context: CallbackContext) -> int:

    print(123)
    print(context.user_data)
    if 'EDIT_USER_ID' in context.user_data:
    
        print('SKIP PHOTO DPLASJDAIOHAS9YW98FWYRQ98WFHESU89FHSA9FHD')
        user_id_to_edit = context.user_data['EDIT_USER_ID'] 
        user_data[user_id_to_edit].pop('PHOTO', None)
    update.message.reply_text("<b>Дякуємо, що залишили нову адресу. Ваша інформація буде перебувати на перевірці, і незабаром буде опублікована.</b>", parse_mode='HTML')
    user_id = update.message.chat_id  # Capture user_id
    save_user_data(user_id)  # Pass user_id to function
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

def main() -> None:
    updater = Updater("6868089807:AAEJbKT7t1-w4WK05wkOTqigL7cQ5HE0ohM")
    dispatcher = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(Filters.regex('^Повідомити нову адресу$'), new_address),
            MessageHandler(Filters.regex('^Редактировать адрес$'), edit_address),
        ],
        states={
            EXACT_ADDRESS: [MessageHandler(Filters.text & ~Filters.command, exact_address)],
            DETAILS: [MessageHandler(Filters.text & ~Filters.command, details), CallbackQueryHandler(button, pattern='^skip_details$')],
            PHOTO: [MessageHandler(Filters.all, photo), CallbackQueryHandler(button, pattern='^skip_photo$')],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    conv_handler2 = ConversationHandler(
        entry_points=[CallbackQueryHandler(button, pattern='^yr')],
        states={
            EXACT_ADDRESS: [MessageHandler(Filters.text & ~Filters.command, exact_address)],
            DETAILS: [MessageHandler(Filters.text & ~Filters.command, details)],
            PHOTO: [MessageHandler(Filters.all, updaterPhoto), CommandHandler('skip', skip_photo)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    conv_handler_broadcast = ConversationHandler(
        entry_points=[MessageHandler(Filters.regex('^Рассылка модератором$'), broadcast_moderator)],
        states={
            CHOOSE_city: [CallbackQueryHandler(choose_city)],
            BROADCAST_MSG: [MessageHandler(Filters.all & ~Filters.command, broadcast_to_city)],
            BROADCAST_ALL: [MessageHandler(Filters.all & ~Filters.command, broadcast_to_all_cities)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    conv_handler_message = ConversationHandler(
        entry_points=[MessageHandler(Filters.regex('^Відкрити карту адрес'), broadcast_message)],
        states={
            CHOOSE_city: [CallbackQueryHandler(choose_city)],
            BROADCAST_MSG: [MessageHandler(Filters.all & ~Filters.command, broadcast_to_city)],
            BROADCAST_ALL: [MessageHandler(Filters.all & ~Filters.command, broadcast_to_all_cities)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    dispatcher.add_handler(conv_handler_broadcast)
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("city", city))
    dispatcher.add_handler(conv_handler_message)
    dispatcher.add_handler(conv_handler2)
    dispatcher.add_handler(conv_handler)
    dispatcher.add_handler(CallbackQueryHandler(button))
    dispatcher.add_error_handler(error_handler)


    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
