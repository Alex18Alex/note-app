import pandas as pd
import sqlite3
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error
import json
from datetime import datetime, timedelta


class DebtForecaster:
    def __init__(self, database_path):
        self.database_path = database_path

    def generate_forecast(self, dataset_id, months=6):
        """Генерация прогноза задолженности"""
        conn = sqlite3.connect(self.database_path)

        # Получаем исторические данные
        query = '''
                SELECT period, \
                       SUM(charge_amount - payment_amount) as monthly_debt
                FROM payment_records
                WHERE dataset_id = ?
                GROUP BY period
                ORDER BY period \
                '''

        df = pd.read_sql_query(query, conn, params=[dataset_id])
        conn.close()

        if len(df) < 3:
            return {'error': 'Недостаточно данных для прогнозирования. Нужно минимум 3 периода.'}

        # Подготовка данных для модели
        df['period_num'] = range(len(df))

        # Простая линейная регрессия для прогноза
        X = df[['period_num']].values
        y = df['monthly_debt'].values

        model = LinearRegression()
        model.fit(X, y)

        # Прогноз на будущие периоды
        future_periods = list(range(len(df), len(df) + months))
        X_future = np.array(future_periods).reshape(-1, 1)
        y_pred = model.predict(X_future)

        # Генерация дат для будущих периодов
        last_period = df['period'].iloc[-1]
        last_date = datetime.strptime(last_period, '%Y-%m')

        future_dates = []
        for i in range(months):
            next_date = last_date + timedelta(days=30 * (i + 1))
            future_dates.append(next_date.strftime('%Y-%m'))

        # Оценка точности модели
        y_actual = df['monthly_debt'].values
        y_fitted = model.predict(X)

        mae = mean_absolute_error(y_actual, y_fitted)
        mse = mean_squared_error(y_actual, y_fitted)
        rmse = np.sqrt(mse)

        # Подготовка результатов
        historical_data = [
            {'period': row['period'], 'debt': row['monthly_debt']}
            for _, row in df.iterrows()
        ]

        forecast_data = [
            {'period': period, 'debt': float(debt)}
            for period, debt in zip(future_dates, y_pred)
        ]

        return {
            'historical': historical_data,
            'forecast': forecast_data,
            'accuracy_metrics': {
                'mae': round(float(mae), 2),
                'rmse': round(float(rmse), 2),
                'r_squared': round(model.score(X, y), 4)
            },
            'model_info': 'Линейная регрессия',
            'forecast_months': months
        }