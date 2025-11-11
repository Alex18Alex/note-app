import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, request, jsonify, render_template
import psycopg2
from datetime import datetime
import os

app = Flask(__name__)

# Настройка логирования Flask
handler = RotatingFileHandler('flask_app.log', maxBytes=10000, backupCount=3)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - [IP: %(client_ip)s] - %(message)s')
handler.setFormatter(formatter)
app.logger.addHandler(handler)

# Конфигурация БД
DB_CONFIG = {
    'host': 'localhost',
    'database': 'notes_app',
    'user': 'notes_user',
    'password': 'password123'
}


class CustomLogger:
    @staticmethod
    def log_event(level, message, ip=None):
        if ip is None:
            ip = request.remote_addr if request else 'unknown'

        log_message = f"{datetime.now().isoformat()} - {level} - [IP: {ip}] - {message}"

        # Запись в общий лог
        with open('application.log', 'a') as f:
            f.write(log_message + '\n')

        # Также логируем через стандартный логгер Flask
        if level == 'ERROR':
            app.logger.error(f"{message} - IP: {ip}")
        elif level == 'WARNING':
            app.logger.warning(f"{message} - IP: {ip}")
        else:
            app.logger.info(f"{message} - IP: {ip}")


def get_db_connection():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        CustomLogger.log_event('INFO', 'Database connection established')
        return conn
    except Exception as e:
        CustomLogger.log_event('ERROR', f'Database connection failed: {str(e)}')
        return None


@app.route('/')
def index():
    CustomLogger.log_event('INFO', 'Accessed home page')
    return render_template('index.html')


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            # ВАЖНО: Это уязвимый код для демонстрации SQL инъекций
            query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
            CustomLogger.log_event('INFO', f'Login attempt - SQL: {query}')

            cursor.execute(query)
            user = cursor.fetchone()

            if user:
                CustomLogger.log_event('INFO', 'Successful login')
                return jsonify({'status': 'success'})
            else:
                CustomLogger.log_event('WARNING', 'Failed login attempt')
                return jsonify({'status': 'failure'})

        except Exception as e:
            CustomLogger.log_event('ERROR', f'Login error: {str(e)}')
            return jsonify({'status': 'error'})
        finally:
            conn.close()

    return jsonify({'status': 'error'})


@app.route('/admin')
def admin_panel():
    CustomLogger.log_event('WARNING', 'Attempt to access admin panel')
    return jsonify({'error': 'Access denied'}), 403


@app.route('/api/delete/<int:note_id>')
def delete_note(note_id):
    CustomLogger.log_event('INFO', f'Delete note attempt - ID: {note_id}')
    return jsonify({'status': 'success'})


@app.route('/api/users')
def get_users():
    CustomLogger.log_event('INFO', 'Accessed users API')
    return jsonify({'users': []})


if __name__ == '__main__':
    # Создаем файлы логов если их нет
    for log_file in ['application.log', 'flask_app.log', 'postgresql.log']:
        if not os.path.exists(log_file):
            open(log_file, 'w').close()

    app.run(debug=False, host='0.0.0.0', port=5000)