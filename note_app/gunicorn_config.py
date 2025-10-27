# gunicorn_config.py
import multiprocessing

# Базовые настройки
bind = "127.0.0.1:5000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"

# Скрытие информации о сервере
server_header = False
date_header = False

# Безопасность
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190

# Логирование
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Производительность
max_requests = 1000
max_requests_jitter = 100
timeout = 60
keepalive = 2

# Дополнительные заголовки безопасности
def post_fork(server, worker):
    # Убираем информацию о версиях
    import os
    os.environ.pop('SERVER_SOFTWARE', None)