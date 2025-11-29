import time
import logging
from telebot import types
from bot import bot
from handlers.single_handler import handle_number
from handlers.mass_handler import handle_excel_file, handle_mass_send_callback
from status import check_greenapi_status

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


@bot.message_handler(commands=['start'])
def send_welcome(message):
    logging.info(f"Пользователь {message.from_user.id} нажал start")

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    mass_send = types.KeyboardButton("📤 Массовая отправка (Excel)")
    single_send = types.KeyboardButton("✍️ Одиночная отправка")
    markup.add(mass_send, single_send)

    mess = f'Добрый день! <i>Чем я могу сегодня Вам помочь?</i>'
    bot.send_message(message.chat.id, mess, parse_mode='HTML', reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == "📤 Массовая отправка (Excel)")
def handle_mass_button(message):
    mess = (
        "📤 Отправьте Excel файл (.xlsx) со следующими колонками:\n\n"
        "• <b>Имя</b> - имя контакта\n"
        "• <b>Номер</b> - номер телефона (79991234567)\n"
        "• <b>Текст</b> - текст сообщения (используйте {имя} для подстановки)\n"
        "• <b>Результат</b> - оставьте пустым"
    )
    bot.send_message(message.chat.id, mess, parse_mode='HTML')
    bot.register_next_step_handler(message, handle_excel_file)


@bot.message_handler(func=lambda message: message.text == "✍️ Одиночная отправка")
def handle_single_button(message):
    mess = 'Введите номер телефона в формате +79*********'
    bot.send_message(message.chat.id, mess, parse_mode='HTML')
    bot.register_next_step_handler(message, handle_number)


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    logging.info(f"Пользователь {user_id} нажал: {call.data}")

    if call.data in ['start_mass_send', 'cancel_mass_send']:
        handle_mass_send_callback(call)

@bot.message_handler(commands=['status'])
def check_status(message):
    status = check_greenapi_status()
    bot.send_message(message.chat.id, f"📊 Статус Green-API: {status}")

def main():
    logging.info("Запуск бота...")
    while True:
        try:
            bot.polling(none_stop=True, timeout=60, skip_pending=True)
        except Exception as e:
            logging.error(f"Ошибка при запуске бота: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()