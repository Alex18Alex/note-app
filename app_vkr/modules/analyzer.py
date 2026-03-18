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