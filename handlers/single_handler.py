import requests
import logging
import re
from bot import *
from keys import InstanceWhatsup, ApiWhatsup

def handle_number(message):
    user_id = message.from_user.id
    try:
        if len(str(message.text)) == 12 and str(message.text)[0] == '+' and str(message.text)[1] == '7':
            phone = str(message.text)
            if phone[2:].isdigit():
                # Сохраняем номер в словарь пользователя
                if user_id not in user_data:
                    user_data[user_id] = {}
                user_data[user_id]['phone'] = phone

                mess = "Теперь введите текст сообщения"
                bot.send_message(message.chat.id, mess, parse_mode='HTML')
                bot.register_next_step_handler(message, handle_message)
            else:
                bot.reply_to(message, '❌ Номер должен содержать только цифры после +7')
        else:
            bot.reply_to(message, '❌ Неверный формат. Используйте: +79123456789')

    except Exception as e:
        logging.error(f"Ошибка при обработке номера: {e}")
        bot.reply_to(message, '❌ Произошла ошибка. Проверьте правильность введенного номера.')


def handle_message(message):
    user_id = message.from_user.id
    try:
        # Сохраняем текст сообщения
        if user_id in user_data:
            user_data[user_id]['text'] = message.text

            mess = '✅ Отлично, текст корректный! Отправляю сообщение...'
            bot.send_message(message.chat.id, mess, parse_mode='HTML')

            # Получаем данные и отправляем
            phone = user_data[user_id]['phone']
            text = user_data[user_id]['text']

            # Вызываем функцию отправки с двумя аргументами
            send_whatsapp_greenapi(phone, text, message.chat.id)

        else:
            bot.reply_to(message, '❌ Что-то пошло не так. Начните заново /start')
    except Exception as e:
        logging.error(f"Ошибка при обработке сообщения: {e}")
        bot.reply_to(message, '❌ Произошла ошибка при обработке сообщения.')


def format_phone_for_greenapi(phone):
    """
    Приводит номер к формату 79123456789@c.us
    """
    # Убираем все кроме цифр
    clean_phone = re.sub(r'\D', '', phone)

    # Приводим к формату 79123456789
    if clean_phone.startswith('7') and len(clean_phone) == 11:
        formatted = clean_phone
    elif clean_phone.startswith('8') and len(clean_phone) == 11:
        formatted = '7' + clean_phone[1:]
    elif len(clean_phone) == 10:
        formatted = '7' + clean_phone
    else:
        return None

    return f"{formatted}@c.us"


def send_whatsapp_greenapi(phone, message_text, chat_id):
    try:
        idInstance = InstanceWhatsup
        apiTokenInstance = ApiWhatsup

        # Форматируем номер
        chat_id_formatted = format_phone_for_greenapi(phone)

        if not chat_id_formatted:
            bot.send_message(chat_id, f'❌ Неверный формат номера: {phone}')
            return

        url = f"https://api.green-api.com/waInstance{idInstance}/sendMessage/{apiTokenInstance}"

        payload = {
            "chatId": chat_id_formatted,
            "message": message_text
        }

        # Логируем запрос
        logging.info(f"Green-API запрос: {payload}")

        response = requests.post(url, json=payload)
        result = response.json()

        # Логируем ответ
        logging.info(f"Green-API ответ: {result}")

        if response.status_code == 200:
            message_id = result.get('idMessage', 'unknown')
            bot.send_message(
                chat_id,
                f'✅ Сообщение отправлено!\n'
                f'📞 На номер: {phone}\n'
                f'💬 Текст: {message_text}'
            )
        else:
            error_msg = result.get('message', 'Неизвестная ошибка')
            bot.send_message(
                chat_id,
                f'❌ Ошибка Green-API:\n{error_msg}\n'
                f'📞 Номер: {phone}\n'
                f'🔧 Код ошибки: {response.status_code}'
            )

    except Exception as e:
        logging.error(f"Ошибка отправки: {e}")
        bot.send_message(chat_id, f'❌ Ошибка подключения: {e}')
    except Exception as e:
        logging.error(f"Ошибка отправки: {e}")
        bot.send_message(chat_id, f'❌ Ошибка подключения: {e}')