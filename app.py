import os
import logging
import secrets
from flask import Flask
from logging.handlers import RotatingFileHandler

log_formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
log_handler = RotatingFileHandler('app.log', maxBytes=10*1024*1024, backupCount=5)
log_handler.setFormatter(log_formatter)
log_handler.setLevel(logging.INFO)  # Используем INFO для продакшена

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(log_handler)

if os.environ.get('FLASK_ENV') != 'development':
    logging.getLogger('werkzeug').setLevel(logging.WARNING)

app = Flask(__name__)

app.secret_key = os.environ.get('SESSION_SECRET') or secrets.token_hex(32)

app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # Уменьшен до 5MB для безопасности

upload_dir = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'])
try:
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir, mode=0o750)  # Ограниченные права доступа
    os.chmod(upload_dir, 0o750)  # Устанавливаем права только для владельца и группы
except OSError as e:
    logger.error(f'Ошибка создания директории загрузки: {e}')
    raise

from models import init_db
from routes import *

with app.app_context():
    try:
        init_db()
        logger.info('База данных успешно инициализирована.')
    except Exception as e:
        logger.error(f'Ошибка инициализации базы данных: {e}')
        raise
    