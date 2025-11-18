import time
import re
from collections import defaultdict
from datetime import datetime, timedelta
import smtplib
import threading


class SIEMMonitor:
    def __init__(self):
        self.log_file = 'application.log'
        self.alerts_file = 'security_alerts.log'
        self.report_file = f"daily_security_report_{datetime.now().strftime('%Y%m%d')}.txt"

        # Статистика для отчета
        self.stats = {
            'total_requests': 0,
            'incidents': 0,
            'incident_types': defaultdict(int),
            'suspicious_ips': defaultdict(int),
            'start_time': datetime.now()
        }

        # Хранилище для обнаружения brute force атак
        self.failed_logins = defaultdict(list)

        # Паттерны для обнаружения SQL инъекций
        self.sql_injection_patterns = [
            # Только подозрительные конструкции
            r"'.*OR.*1=1",
            r"UNION.*SELECT.*FROM",
            r"DROP TABLE.*--",
            r"'.*--",
            # Комбинации с комментариями
            r"INSERT.*INTO.*--",
            r"UPDATE.*SET.*--",
        ]

        # Защищенные эндпоинты для мониторинга
        self.protected_endpoints = [
            '/admin',
            '/api/delete',
            '/api/users',
            '/config',
            '/backup'
        ]

    def tail_log(self):
        """Чтение лог файла в реальном времени"""
        try:
            with open(self.log_file, 'r') as f:
                # Перемещаемся в конец файла
                f.seek(0, 2)

                while True:
                    line = f.readline()
                    if not line:
                        time.sleep(0.1)
                        continue

                    yield line
        except FileNotFoundError:
            print(f"Лог файл {self.log_file} не найден!")
            return

    def parse_log_line(self, line):
        """Парсинг строки лога"""
        try:
            # Формат: timestamp - level - [IP: xxx.xxx.xxx.xxx] - message
            parts = line.strip().split(' - ', 3)
            if len(parts) >= 4:
                timestamp_str, level, ip_info, message = parts

                # Извлекаем IP адрес
                ip_match = re.search(r'\[IP: ([\d\.]+)\]', ip_info)
                ip = ip_match.group(1) if ip_match else 'unknown'

                timestamp = datetime.fromisoformat(timestamp_str)

                return {
                    'timestamp': timestamp,
                    'level': level,
                    'ip': ip,
                    'message': message,
                    'raw_line': line.strip()
                }
            return None
        except Exception as e:
            print(f"Ошибка парсинга лога: {e}")
            return None

    def detect_brute_force(self, log_entry):
        """Обнаружение множественных неудачных попыток входа"""
        if 'Failed login attempt' in log_entry['message']:
            ip = log_entry['ip']
            current_time = log_entry['timestamp']

            # Добавляем попытку в историю
            self.failed_logins[ip].append(current_time)

            # Удаляем старые попытки (старше 1 минуты)
            time_threshold = current_time - timedelta(minutes=1)
            self.failed_logins[ip] = [
                t for t in self.failed_logins[ip] if t > time_threshold
            ]

            # Проверяем количество попыток
            if len(self.failed_logins[ip]) >= 5:
                self.trigger_alert(
                    'BRUTE_FORCE',
                    f"Обнаружена brute force атака с IP {ip}. "
                    f"{len(self.failed_logins[ip])} неудачных попыток за 1 минуту.",
                    log_entry
                )
                # Очищаем историю после алерта
                self.failed_logins[ip] = []

    def detect_sql_injection(self, log_entry):
        """Обнаружение SQL инъекций"""
        message = log_entry['message']

        for pattern in self.sql_injection_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                self.trigger_alert(
                    'SQL_INJECTION',
                    f"Обнаружена потенциальная SQL инъекция: {pattern}",
                    log_entry
                )
                break

    def detect_suspicious_access(self, log_entry):
        """Обнаружение подозрительного доступа к защищенным эндпоинтам"""
        message = log_entry['message']

        for endpoint in self.protected_endpoints:
            if endpoint in message:
                if '403' in message or 'Access denied' in message:
                    self.trigger_alert(
                        'UNAUTHORIZED_ACCESS',
                        f"Попытка несанкционированного доступа к {endpoint}",
                        log_entry
                    )
                elif '404' in message:
                    self.trigger_alert(
                        'ENDPOINT_SCANNING',
                        f"Сканирование эндпоинта {endpoint}",
                        log_entry
                    )

    def trigger_alert(self, alert_type, description, log_entry):
        """Триггер алерта"""
        alert_time = datetime.now()
        alert_message = (
            f"{alert_time.isoformat()} - ALERT - {alert_type} - "
            f"[IP: {log_entry['ip']}] - {description} - "
            f"Original log: {log_entry['raw_line']}"
        )

        # Запись в файл алертов
        with open(self.alerts_file, 'a') as f:
            f.write(alert_message + '\n')

        # Вывод в консоль с цветом
        self.print_colored_alert(alert_type, alert_message)

        # Обновление статистики
        self.stats['incidents'] += 1
        self.stats['incident_types'][alert_type] += 1
        self.stats['suspicious_ips'][log_entry['ip']] += 1

    def print_colored_alert(self, alert_type, message):
        """Цветной вывод алертов в консоль"""
        colors = {
            'BRUTE_FORCE': '\033[91m',  # Красный
            'SQL_INJECTION': '\033[93m',  # Желтый
            'UNAUTHORIZED_ACCESS': '\033[95m',  # Фиолетовый
            'ENDPOINT_SCANNING': '\033[96m'  # Голубой
        }

        color = colors.get(alert_type, '\033[0m')
        reset = '\033[0m'

        print(f"{color}[!] {message}{reset}")

    def generate_daily_report(self):
        """Генерация ежедневного отчета"""
        end_time = datetime.now()
        duration = end_time - self.stats['start_time']

        report = f"""
ЕЖЕДНЕВНЫЙ ОТЧЕТ ПО БЕЗОПАСНОСТИ
Дата генерации: {end_time.strftime('%Y-%m-%d %H:%M:%S')}
Период мониторинга: {duration}

ОБЩАЯ СТАТИСТИКА:
- Всего обработано запросов: {self.stats['total_requests']}
- Всего инцидентов безопасности: {self.stats['incidents']}
- Время мониторинга: {duration}

ДЕТАЛИ ИНЦИДЕНТОВ:
"""

        for incident_type, count in self.stats['incident_types'].items():
            report += f"- {incident_type}: {count} случаев\n"

        report += f"\nПОДОЗРИТЕЛЬНЫЕ IP АДРЕСА:\n"
        for ip, count in self.stats['suspicious_ips'].items():
            report += f"- {ip}: {count} инцидентов\n"

        report += f"\nРЕКОМЕНДАЦИИ:\n"
        if self.stats['incidents'] > 10:
            report += "- Высокий уровень угроз. Рекомендуется усилить меры безопасности.\n"
        elif self.stats['incidents'] > 5:
            report += "- Средний уровень угроз. Рекомендуется проверить конфигурацию.\n"
        else:
            report += "- Низкий уровень угроз. Система работает стабильно.\n"

        # Запись отчета в файл
        with open(self.report_file, 'w') as f:
            f.write(report)

        print(f"\nОтчет сохранен в файл: {self.report_file}")
        return report

    def monitor(self):
        """Основной цикл мониторинга"""
        print("Запуск SIEM мониторинга...")
        print("Отслеживаемые угрозы:")
        print("- Brute force атаки (5+ неудачных логинов за 1 минуту)")
        print("- SQL инъекции")
        print("- Несанкционированный доступ к защищенным эндпоинтам")
        print("- Сканирование уязвимостей")
        print("-" * 50)

        for line in self.tail_log():
            self.stats['total_requests'] += 1

            log_entry = self.parse_log_line(line)
            if log_entry:
                # Проверяем все типы угроз
                self.detect_brute_force(log_entry)
                self.detect_sql_injection(log_entry)
                self.detect_suspicious_access(log_entry)

    def start_scheduled_reporting(self):
        """Запуск генерации отчетов по расписанию"""

        def schedule_reports():
            while True:
                # Ждем до 23:59 для генерации ежедневного отчета
                now = datetime.now()
                target_time = now.replace(hour=23, minute=59, second=0, microsecond=0)

                if now > target_time:
                    target_time += timedelta(days=1)

                sleep_seconds = (target_time - now).total_seconds()
                time.sleep(sleep_seconds)

                self.generate_daily_report()
                print(f"Ежедневный отчет сгенерирован в {datetime.now()}")

        thread = threading.Thread(target=schedule_reports, daemon=True)
        thread.start()


def main():
    monitor = SIEMMonitor()

    # Запуск генерации отчетов по расписанию
    monitor.start_scheduled_reporting()

    try:
        monitor.monitor()
    except KeyboardInterrupt:
        print("\nОстановка мониторинга...")
        monitor.generate_daily_report()


if __name__ == '__main__':
    main()