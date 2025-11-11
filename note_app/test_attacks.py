import requests
import time
from datetime import datetime


def test_brute_force():
    """Тест brute force атаки"""
    print("Тестирование brute force атаки...")
    base_url = "http://localhost:5000"

    for i in range(10):
        response = requests.post(f"{base_url}/login", json={
            'username': f'user{i}',
            'password': 'wrongpassword'
        })
        print(f"Попытка {i + 1}: {response.status_code}")
        time.sleep(1)


def test_sql_injection():
    """Тест SQL инъекций"""
    print("Тестирование SQL инъекций...")
    base_url = "http://localhost:5000"

    payloads = [
        {"username": "admin' OR '1'='1", "password": "any"},
        {"username": "admin", "password": "' OR 1=1--"},
        {"username": "admin'; DROP TABLE users--", "password": "any"}
    ]

    for payload in payloads:
        response = requests.post(f"{base_url}/login", json=payload)
        print(f"Инъекция: {payload} - Status: {response.status_code}")
        time.sleep(2)


def test_suspicious_access():
    """Тест подозрительного доступа"""
    print("Тестирование подозрительного доступа...")
    base_url = "http://localhost:5000"

    endpoints = ['/admin', '/api/delete/1', '/api/users', '/backup', '/config']

    for endpoint in endpoints:
        response = requests.get(f"{base_url}{endpoint}")
        print(f"Endpoint: {endpoint} - Status: {response.status_code}")
        time.sleep(1)


if __name__ == '__main__':
    print("Запуск тестов безопасности...")
    time.sleep(2)

    test_brute_force()
    time.sleep(5)

    test_sql_injection()
    time.sleep(5)

    test_suspicious_access()

    print("Тестирование завершено!")