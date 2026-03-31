import sqlite3
import pandas as pd
import json
from datetime import datetime


class DebtAnalyzer:
    def __init__(self, database_path):
        self.database_path = database_path

    def calculate_kpi(self, dataset_id):
        """Расчет ключевых показателей эффективности"""
        conn = sqlite3.connect(self.database_path)

        query = '''
                SELECT account_id, \
                       period, \
                       service_type, \
                       charge_amount, \
                       payment_amount, \
                       (charge_amount - payment_amount) as debt_amount
                FROM payment_records
                WHERE dataset_id = ? \
                '''

        df = pd.read_sql_query(query, conn, params=[dataset_id])
        conn.close()

        if df.empty:
            return {}

        # Основные KPI
        total_debt = (df['charge_amount'] - df['payment_amount']).sum()
        avg_debt_per_account = df.groupby('account_id')['debt_amount'].sum().mean()

        # Определяем должников (суммарный долг > 0)
        account_debts = df.groupby('account_id')['debt_amount'].sum()
        debtors_count = (account_debts > 0).sum()
        total_accounts = len(account_debts)
        debtors_percentage = (debtors_count / total_accounts * 100) if total_accounts > 0 else 0

        # Динамика по месяцам
        df['period_dt'] = pd.to_datetime(df['period'], format='%Y-%m', errors='coerce')
        monthly_data = df.groupby('period_dt').agg({
            'charge_amount': 'sum',
            'payment_amount': 'sum',
            'debt_amount': 'sum'
        }).reset_index()

        return {
            'total_debt': round(total_debt, 2),
            'avg_debt_per_account': round(avg_debt_per_account, 2),
            'debtors_count': int(debtors_count),
            'total_accounts': int(total_accounts),
            'debtors_percentage': round(debtors_percentage, 2),
            'collection_rate': round(
                (df['payment_amount'].sum() / df['charge_amount'].sum() * 100) if df['charge_amount'].sum() > 0 else 0,
                2),
            'monthly_data': monthly_data.to_dict('records')
        }

    def get_charts_data(self, dataset_id):
        """Подготовка данных для графиков"""
        conn = sqlite3.connect(self.database_path)

        # Данные для графика динамики
        dynamic_query = '''
                        SELECT period, \
                               SUM(charge_amount)                  as total_charge, \
                               SUM(payment_amount)                 as total_payment, \
                               SUM(charge_amount - payment_amount) as total_debt
                        FROM payment_records
                        WHERE dataset_id = ?
                        GROUP BY period
                        ORDER BY period \
                        '''

        dynamic_df = pd.read_sql_query(dynamic_query, conn, params=[dataset_id])

        # Данные для структуры долга по услугам
        service_query = '''
                        SELECT service_type, \
                               SUM(charge_amount - payment_amount) as service_debt
                        FROM payment_records
                        WHERE dataset_id = ?
                        GROUP BY service_type \
                        '''

        service_df = pd.read_sql_query(service_query, conn, params=[dataset_id])

        # Топ должников
        debtors_query = '''
                        SELECT account_id, \
                               resident_name, \
                               address, \
                               SUM(charge_amount - payment_amount) as total_debt
                        FROM payment_records
                        WHERE dataset_id = ?
                        GROUP BY account_id, resident_name, address
                        HAVING total_debt > 0
                        ORDER BY total_debt DESC LIMIT 10 \
                        '''

        debtors_df = pd.read_sql_query(debtors_query, conn, params=[dataset_id])
        conn.close()

        return {
            'dynamic_data': {
                'periods': dynamic_df['period'].tolist(),
                'charges': dynamic_df['total_charge'].tolist(),
                'payments': dynamic_df['total_payment'].tolist(),
                'debts': dynamic_df['total_debt'].tolist()
            },
            'service_data': {
                'services': service_df['service_type'].tolist(),
                'debts': service_df['service_debt'].tolist()
            },
            'debtors_data': debtors_df.to_dict('records')
        }

    def get_debt_aging(self, dataset_id):
        """
        Анализ возрастной структуры задолженности
        Классифицирует долги по срокам: 0-30, 31-60, 61-90, более 90 дней
        """
        try:
            conn = sqlite3.connect(self.database_path)

            # Получаем все записи о платежах
            query = '''
                    SELECT period,
                           charge_amount,
                           payment_amount,
                           (charge_amount - payment_amount) as debt_amount
                    FROM payment_records
                    WHERE dataset_id = ?
                    '''

            df = pd.read_sql_query(query, conn, params=[dataset_id])
            conn.close()

            # Если данных нет
            if df.empty:
                return {'0-30 дней': 0, '31-60 дней': 0, '61-90 дней': 0, 'более 90 дней': 0}

            # Только записи с долгом
            df_debt = df[df['debt_amount'] > 0].copy()
            if df_debt.empty:
                return {'0-30 дней': 0, '31-60 дней': 0, '61-90 дней': 0, 'более 90 дней': 0}

            # Находим последний период в данных
            max_period = df_debt['period'].max()
            reference_date = pd.to_datetime(max_period + '-01', format='%Y-%m-%d')

            # Преобразуем период в дату
            df_debt['period_date'] = pd.to_datetime(df_debt['period'] + '-01', format='%Y-%m-%d')

            # Рассчитываем возраст долга в днях
            df_debt['days'] = (reference_date - df_debt['period_date']).dt.days
            df_debt['days'] = df_debt['days'].clip(lower=0)

            # Классификация по срокам
            aging = {
                '0-30 дней': float(df_debt[df_debt['days'] <= 30]['debt_amount'].sum()),
                '31-60 дней': float(df_debt[(df_debt['days'] > 30) & (df_debt['days'] <= 60)]['debt_amount'].sum()),
                '61-90 дней': float(df_debt[(df_debt['days'] > 60) & (df_debt['days'] <= 90)]['debt_amount'].sum()),
                'более 90 дней': float(df_debt[df_debt['days'] > 90]['debt_amount'].sum())
            }

            return aging

        except Exception as e:
            print(f"Ошибка в get_debt_aging: {e}")
            return {'0-30 дней': 0, '31-60 дней': 0, '61-90 дней': 0, 'более 90 дней': 0}