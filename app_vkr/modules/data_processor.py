import pandas as pd
import sqlite3
from datetime import datetime
import uuid
import os


class DataProcessor:
    def __init__(self, database_path):
        self.database_path = database_path

    def process_uploaded_file(self, file):
        """Обрабатывает загруженный файл с данными"""
        # Сохраняем файл временно
        filename = f"upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
        filepath = os.path.join('uploads', filename)
        file.save(filepath)

        try:
            # Читаем файл в зависимости от формата
            if file.filename.endswith('.csv'):
                df = pd.read_csv(filepath, encoding='utf-8')
            else:
                df = pd.read_excel(filepath)

            # Валидация данных
            df = self._validate_data(df)

            # Сохраняем в базу данных
            dataset_id = self._save_to_database(df, file.filename)

            # Удаляем временный файл
            os.remove(filepath)

            return {
                'success': True,
                'dataset_id': dataset_id,
                'records_processed': len(df),
                'message': f'Успешно обработано {len(df)} записей'
            }

        except Exception as e:
            # Удаляем временный файл в случае ошибки
            if os.path.exists(filepath):
                os.remove(filepath)
            raise e

    def _validate_data(self, df):
        """Валидация и очистка данных"""
        required_columns = ['account_id', 'period', 'charge_amount', 'payment_amount']

        # Проверяем наличие обязательных колонок
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f'Отсутствует обязательная колонка: {col}')

        # Добавляем недостающие колонки с значениями по умолчанию
        if 'address' not in df.columns:
            df['address'] = 'Не указан'
        if 'resident_name' not in df.columns:
            df['resident_name'] = 'Не указан'
        if 'service_type' not in df.columns:
            df['service_type'] = 'Коммунальные услуги'

        # Очистка данных
        df = df.dropna(subset=required_columns)
        df['charge_amount'] = pd.to_numeric(df['charge_amount'], errors='coerce').fillna(0)
        df['payment_amount'] = pd.to_numeric(df['payment_amount'], errors='coerce').fillna(0)

        # Удаляем строки с отрицательными значениями
        df = df[(df['charge_amount'] >= 0) & (df['payment_amount'] >= 0)]

        return df

    def _save_to_database(self, df, filename):
        """Сохраняет данные в базу данных"""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()

        # Создаем запись о датасете
        cursor.execute(
            'INSERT INTO datasets (name, description) VALUES (?, ?)',
            (filename, f'Загружено {datetime.now().strftime("%Y-%m-%d %H:%M")}')
        )
        dataset_id = cursor.lastrowid

        # Сохраняем записи о платежах
        for _, row in df.iterrows():
            cursor.execute('''
                           INSERT INTO payment_records
                           (dataset_id, account_id, address, resident_name, period, service_type, charge_amount,
                            payment_amount)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                           ''', (
                               dataset_id,
                               str(row['account_id']),
                               str(row['address']),
                               str(row['resident_name']),
                               str(row['period']),
                               str(row['service_type']),
                               float(row['charge_amount']),
                               float(row['payment_amount'])
                           ))

        conn.commit()
        conn.close()

        return dataset_id