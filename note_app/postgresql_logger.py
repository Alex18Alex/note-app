import logging
import psycopg2
from datetime import datetime
import time


def setup_postgresql_logging():
    """Настройка логирования PostgreSQL запросов"""

    while True:
        try:
            # Подключаемся к БД для мониторинга
            conn = psycopg2.connect(
                host='localhost',
                database='notes_app',
                user='notes_user',
                password='password123'
            )

            # Эмулируем логи PostgreSQL
            sample_queries = [
                "SELECT * FROM users WHERE username = 'admin'",
                "INSERT INTO notes (title, content) VALUES ('Test', 'Content')",
                "SELECT * FROM users WHERE username = 'admin' OR 1=1",
                "DROP TABLE users",
                "SELECT username, password FROM users UNION SELECT 1, 2",
                "UPDATE users SET password = 'newpass' WHERE id = 1"
            ]

            for query in sample_queries:
                log_entry = f"{datetime.now().isoformat()} - POSTGRES - QUERY - {query}\n"

                # Запись в общий лог
                with open('application.log', 'a') as f:
                    f.write(log_entry)

                # Запись в лог PostgreSQL
                with open('postgresql.log', 'a') as f:
                    f.write(log_entry)

                time.sleep(10)  # Ждем 10 секунд между запросами

        except Exception as e:
            error_log = f"{datetime.now().isoformat()} - POSTGRES - ERROR - {str(e)}\n"
            with open('application.log', 'a') as f:
                f.write(error_log)
            with open('postgresql.log', 'a') as f:
                f.write(error_log)
            time.sleep(30)


if __name__ == '__main__':
    setup_postgresql_logging()