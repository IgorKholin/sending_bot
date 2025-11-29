import pandas as pd
import logging
import os
from telebot import types
import requests
import tempfile
import time
import threading
from keys import InstanceWhatsup, ApiWhatsup

# Временное хранилище для файлов пользователей
user_files = {}


def validate_phone_for_excel(phone):
    """Валидация номера для Excel файла"""
    if pd.isna(phone):
        return False

    phone = str(phone).strip()
    clean_phone = ''.join(filter(str.isdigit, str(phone)))

    if len(clean_phone) == 11:
        if clean_phone.startswith('7'):
            return clean_phone  # 79123456789 → 79123456789
        elif clean_phone.startswith('8'):
            return '7' + clean_phone[1:]  # 89123456789 → 79123456789
    elif len(clean_phone) == 10:
        return '7' + clean_phone  # 9123456789 → 79123456789

    return None

def check_excel_structure(file_path):
    """Проверка структуры Excel файла"""
    try:
        df = pd.read_excel(file_path)

        required_columns = ['Имя', 'Номер', 'Текст']
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            return False, f"Отсутствуют колонки: {', '.join(missing_columns)}"

        if len(df) == 0:
            return False, "Файл не содержит данных"

        return True, df

    except Exception as e:
        return False, f"Ошибка чтения файла: {str(e)}"


def handle_excel_file(message):
    """Обработка полученного Excel файла"""
    try:
        from main import bot

        user_id = message.from_user.id

        if not message.document:
            bot.reply_to(message, "❌ Пожалуйста, отправьте файл в формате .xlsx")
            return

        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
            temp_file.write(downloaded_file)
            temp_path = temp_file.name

        is_valid, result = check_excel_structure(temp_path)

        if not is_valid:
            os.unlink(temp_path)
            bot.reply_to(message, f"❌ {result}")
            return

        df = result
        user_files[user_id] = {'file_path': temp_path, 'dataframe': df}

        total_contacts = len(df)
        sample_text = df.iloc[0]['Текст'] if len(df) > 0 else "N/A"

        markup = types.InlineKeyboardMarkup()
        btn_start = types.InlineKeyboardButton("🚀 Начать рассылку", callback_data='start_mass_send')
        btn_cancel = types.InlineKeyboardButton("❌ Отмена", callback_data='cancel_mass_send')
        markup.add(btn_start, btn_cancel)

        info_text = (
            f"✅ Файл успешно проверен!\n\n"
            f"📊 Контактов: {total_contacts}\n"
            f"📝 Пример текста:\n{sample_text}\n\n"
            f"Начать рассылку?"
        )

        bot.send_message(message.chat.id, info_text, reply_markup=markup)

    except Exception as e:
        logging.error(f"Ошибка обработки файла: {e}")
        from main import bot
        bot.reply_to(message, f"❌ Ошибка обработки файла: {e}")


def process_mass_sending(call):
    """Обработка массовой рассылки в отдельном потоке"""
    try:
        # Импортируем внутри функции
        from main import bot

        user_id = call.from_user.id

        if user_id not in user_files:
            bot.send_message(call.message.chat.id, "❌ Файл не найден. Начните заново.")
            return

        file_data = user_files[user_id]
        df = file_data['dataframe']
        file_path = file_data['file_path']

        if 'Результат' not in df.columns:
            df['Результат'] = ''

        # Отправляем начальное сообщение
        bot.send_message(call.message.chat.id, "🔄 Начинаю рассылку...")

        success_count = 0
        error_count = 0
        total_rows = len(df)

        # Обрабатываем строки с увеличенными задержками
        for index, row in df.iterrows():
            try:
                # Пропускаем уже отправленные
                if pd.notna(row.get('Результат')) and 'Успешно' in str(row['Результат']):
                    continue

                name = str(row['Имя']) if pd.notna(row['Имя']) else ''
                phone = row['Номер']
                template_text = str(row['Текст']) if pd.notna(row['Текст']) else ''

                # Валидация номера
                formatted_phone = validate_phone_for_excel(phone)
                if not formatted_phone:
                    df.at[index, 'Результат'] = '❌ Ошибка номера'
                    error_count += 1
                    continue

                # Формируем итоговый текст
                final_text = template_text.replace('{имя}', name)

                # Отправка сообщения
                success = send_whatsapp_message(formatted_phone, final_text)

                if success:
                    df.at[index, 'Результат'] = '✅ Успешно отправлено'
                    success_count += 1
                else:
                    df.at[index, 'Результат'] = '❌ Не удалось отправить'
                    error_count += 1

                # Обновляем прогресс каждые 5 сообщений (реже)
                if (index + 1) % 5 == 0:
                    try:
                        progress = f"📊 Обработано: {index + 1}/{total_rows}\n✅ Успешно: {success_count}\n❌ Ошибок: {error_count}"
                        # Используем answer_callback_query вместо edit_message_text
                        bot.answer_callback_query(call.id, progress, show_alert=True)
                    except:
                        pass

                # УВЕЛИЧИВАЕМ задержку до 5 секунд
                time.sleep(5)

            except Exception as e:
                logging.error(f"Ошибка обработки строки {index}: {e}")
                df.at[index, 'Результат'] = f'❌ Ошибка'
                error_count += 1
                time.sleep(3)

        # Сохраняем результат
        result_file_path = file_path.replace('.xlsx', '_result.xlsx')
        df.to_excel(result_file_path, index=False)

        # Отправляем результат
        with open(result_file_path, 'rb') as result_file:
            bot.send_document(
                call.message.chat.id,
                result_file,
                caption=(
                    f"📊 Рассылка завершена!\n"
                    f"✅ Успешно: {success_count}\n"
                    f"❌ Ошибок: {error_count}"
                )
            )

        # Очищаем временные файлы
        os.unlink(file_path)
        os.unlink(result_file_path)
        if user_id in user_files:
            del user_files[user_id]

    except Exception as e:
        logging.error(f"Ошибка массовой рассылки: {e}")
        from main import bot
        bot.send_message(call.message.chat.id, f"❌ Ошибка рассылки: {e}")


def send_whatsapp_message(phone, message_text):
    """Отправка сообщения через Green-API"""
    try:
        idInstance = InstanceWhatsup
        apiTokenInstance = ApiWhatsup

        chat_id_formatted = f"{phone}@c.us"

        url = f"https://api.green-api.com/waInstance{idInstance}/sendMessage/{apiTokenInstance}"

        payload = {
            "chatId": chat_id_formatted,
            "message": message_text
        }

        response = requests.post(url, json=payload, timeout=60)  # Увеличиваем таймаут
        return response.status_code == 200

    except Exception as e:
        logging.error(f"Ошибка отправки WhatsApp: {e}")
        return False


def handle_mass_send_callback(call):
    """Обработка callback для массовой рассылки"""
    from main import bot

    if call.data == 'start_mass_send':
        # ЗАПУСКАЕМ В ОТДЕЛЬНОМ ПОТОКЕ
        thread = threading.Thread(target=process_mass_sending, args=(call,))
        thread.daemon = True
        thread.start()

        # Сразу отвечаем на callback
        bot.answer_callback_query(call.id, "Рассылка запущена в фоне...")

    elif call.data == 'cancel_mass_send':
        user_id = call.from_user.id
        if user_id in user_files:
            os.unlink(user_files[user_id]['file_path'])
            del user_files[user_id]
        bot.send_message(call.message.chat.id, "❌ Рассылка отменена")