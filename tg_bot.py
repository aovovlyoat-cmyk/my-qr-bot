import os
import telebot
import qrcode
import cv2
import numpy as np
import uuid
from io import BytesIO
from telebot import types
from threading import Thread
from http.server import BaseHTTPRequestHandler, HTTPServer

# Безопасное получение токена из переменных окружения Render
# Если деплоишь локально для тестов, можешь временно заменить на: TOKEN = "твой_токен"
TOKEN = os.environ.get("BOT_TOKEN", "8964389716:AAE5WsnbLQJX3L42BcSQcgvDx8qTU7LCt7U")
bot = telebot.TeleBot(TOKEN)

# Мини-сервер для обмана Render
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"OK")

def run_health_server():
    # Render автоматически передает нужный порт. Если его нет, используем 10000
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    print(f"Мини-сервер для Render успешно запущен на порту {port}")
    server.serve_forever()

# Обработка команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Я твой личный ТГ QR-бот 🤖\n\n"
                          "• Отправь мне любой текст или ссылку — и я сделаю QR-код.\n"
                          "• Отправь мне фото с QR-кодом — и я его расшифрую!")

# Логика ГЕНЕРАТОРА (в личке бота)
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

# Логика СКАНЕРА
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
        bot.reply_to(message, "❌ Не удалось найти или считать QR-код на этом фото.")

# ================= ЧИСТЫЙ ИНЛАЙН, КОТОРЫЙ ШЛЁТ СРАЗУ КАРТИНКУ =================
@bot.inline_handler(lambda query: len(query.query) > 0)
def query_text(inline_query):
    try:
        text_data = inline_query.query.strip()
        
        # 1. Генерируем QR-код в памяти сервера
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(text_data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        bio = BytesIO()
        bio.name = 'inline_qr.png'
        img.save(bio, 'PNG')
        bio.seek(0)
        
        # 2. ХАК: Бот отправляет скрытое фото, чтобы получить рабочий file_id
        sent_msg = bot.send_photo(inline_query.from_user.id, photo=bio, caption="Генерация...")
        file_id = sent_msg.photo[-1].file_id
        
        # Сразу удаляем это скрытое сообщение из лички
        bot.delete_message(inline_query.from_user.id, sent_msg.message_id)
        
        # 3. Отправляем в инлайн КЭШИРОВАННОЕ ФОТО по его file_id
        result = types.InlineQueryResultCachedPhoto(
            id=str(uuid.uuid4()),
            photo_file_id=file_id,
            caption=f"Твой готовый QR-код для: {text_data} 😎"
        )
        
        bot.answer_inline_query(inline_query.id, [result], cache_time=0)
    except Exception as e:
        print(f"Ошибка в инлайн-режиме: {e}")

if __name__ == "__main__":
    # Сначала запускаем фоновый веб-сервер для прохождения проверок Render
    Thread(target=run_health_server, daemon=True).start()
    
    # Затем запускаем основной цикл бота Telegram
    print("Бот успешно запущен и готов к работе...")
    bot.infinity_polling()
