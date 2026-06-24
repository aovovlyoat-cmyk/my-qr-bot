import telebot
import qrcode
import cv2
import numpy as np
import uuid
from io import BytesIO
from telebot import types

# Твой личный токен от BotFather
TOKEN = "8964389716:AAE5WsnbLQJX3L42BcSQcgvDx8qTU7LCt7U"
bot = telebot.TeleBot(TOKEN)

print("Бот успешно запущен и готов к работе...")


# Обработка команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Я твой личный ТГ QR-бот 🤖\n\n"
                          "• Отправь мне любой текст или ссылку — и я сделаю QR-код.\n"
                          "• Отправь мне фото с QR-кодом — и я его расшифрую!")


# Логика ГЕНЕРАТОРА (если пользователь прислал текст или ссылку в ЛС)
@bot.message_handler(content_types=['text'])
def make_qr(message):
    text_data = message.text.strip()

    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(text_data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    bio = BytesIO()
    bio.name = 'qrcode.png'
    img.save(bio, 'PNG')
    bio.seek(0)

    bot.send_photo(message.chat.id, photo=bio, caption="Твой готовый QR-код! 😎")


# Логика СКАНЕРА (если пользователь прислал фото)
@bot.message_handler(content_types=['photo'])
def read_qr(message):
    file_info = bot.get_file(message.photo[-1].file_id)
    downloaded_file = bot.download_file(file_info.file_path)

    nparr = np.frombuffer(downloaded_file, np.uint8)
    cv_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    detector = cv2.QRCodeDetector()
    data, bbox, straight_qrcode = detector.detectAndDecode(cv_img)

    if data:
        bot.reply_to(message, f"🔍 Результат расшифровки:\n\n{data}")
    else:
        bot.reply_to(message,
                     "❌ Не удалось найти или считать QR-код на этом фото. Попробуй сделать картинку четче или ближе.")


# ================= ИСПРАВЛЕННАЯ ЛОГИКА ДЛЯ РАБОТЫ В ЛЮБЫХ ЧАТАХ (INLINE MODE) =================
@bot.inline_handler(lambda query: len(query.query) > 0)
def query_text(inline_query):
    try:
        text_data = inline_query.query.strip()

        # Создаем текстовое сообщение-карточку, которое прокси сервера пропустит без проблем
        result = types.InlineQueryResultArticle(
            id=str(uuid.uuid4()),
            title=f"Создать QR-код для: {text_data}",
            input_message_content=types.InputTextMessageContent(
                message_text=f"✨ *Генерация QR-кода*\n\nЧтобы получить QR-код для текста: `{text_data}`, нажми на кнопку ниже!",
                parse_mode="Markdown"
            ),
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton(
                    text="🤖 Перейти в бота и сгенерировать",
                    url=f"https://t.me"  # Ссылка на твоего бота
                )
            )
        )

        bot.answer_inline_query(inline_query.id, [result])
    except Exception as e:
        print(f"Ошибка в инлайн-режиме: {e}")


# Бесконечный цикл работы бота
bot.infinity_polling()
