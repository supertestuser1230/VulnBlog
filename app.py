import os
import logging
import secrets
from flask import Flask
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
log_formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
log_handler = RotatingFileHandler('app.log', maxBytes=10*1024*1024, backupCount=5)
log_handler.setFormatter(log_formatter)
log_handler.setLevel(logging.WARNING)  # Уровень WARNING для продакшена

logger = logging.getLogger()
logger.setLevel(logging.WARNING)
logger.addHandler(log_handler)

if os.environ.get('FLASK_ENV') != 'development':
    logging.getLogger('werkzeug').setLevel(logging.WARNING)

app = Flask(__name__)
app.secret_key = os.environ['SESSION_SECRET']  # Обязательный ключ из .env
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB

# Настройка директории загрузок
import stat
upload_dir = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'])
try:
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir, mode=0o750)
    os.chmod(upload_dir, 0o750)
    for filename in os.listdir(upload_dir):
        file_path = os.path.join(upload_dir, filename)
        if os.path.isfile(file_path):
            os.chmod(file_path, 0o640)
except OSError as e:
    logger.error(f'Ошибка настройки директории загрузки: {e}')
    raise

# Добавление заголовков безопасности
@app.after_request
def add_security_headers(response):
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
        "style-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
        "img-src 'self' data:; "
        "font-src 'self' https://cdnjs.cloudflare.com;"
    )
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response

from models import init_db
from routes import *

with app.app_context():
    try:
        init_db()
        logger.info('База данных успешно инициализирована.')
    except Exception as e:
        logger.error(f'Ошибка инициализации базы данных: {e}')
        raise

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)
