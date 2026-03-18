import pandas as pd
import sqlite3
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import json
from datetime import datetime, timedelta


class DebtForecaster:
    def __init__(self, database_path):
        self.database_path = database_path

    def generate_forecast(self, dataset_id, months=6):
        """Генерация прогноза задолженности с защитой от отрицательных значений"""
        conn = sqlite3.connect(self.database_path)

        # Получаем исторические данные
        query = '''
                SELECT period,
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
        X = df[['period_num']].values
        y = df['monthly_debt'].values

        # Простая линейная регрессия для прогноза
        model = LinearRegression()
        model.fit(X, y)

        # Прогноз на будущие периоды
        future_periods = list(range(len(df), len(df) + months))
        X_future = np.array(future_periods).reshape(-1, 1)
        y_pred = model.predict(X_future)

        # === ИСПРАВЛЕНИЕ 1: Ограничиваем прогноз снизу нулем ===
        y_pred = np.maximum(y_pred, 0)

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

        # === ИСПРАВЛЕНИЕ 2: Используем r2_score вместо model.score ===
        r_squared = r2_score(y_actual, y_fitted)

        mae = mean_absolute_error(y_actual, y_fitted)
        mse = mean_squared_error(y_actual, y_fitted)
        rmse = np.sqrt(mse)

        # === ИСПРАВЛЕНИЕ 3: Добавляем расчет накопительной задолженности ===
        # Историческая накопительная задолженность
        historical_cumulative = []
        cumulative = 0
        for debt in y_actual:
            cumulative += debt
            historical_cumulative.append(cumulative)

        # Прогнозная накопительная задолженность
        last_cumulative = historical_cumulative[-1] if historical_cumulative else 0
        forecast_cumulative = []
        cumulative = last_cumulative
        for debt in y_pred:
            cumulative += debt
            forecast_cumulative.append(cumulative)

        # === ИСПРАВЛЕНИЕ 4: Добавляем доверительные интервалы ===
        residuals = y_actual - y_fitted
        std_resid = np.std(residuals)

        lower_bound = np.maximum(y_pred - 2 * std_resid, 0)
        upper_bound = y_pred + 2 * std_resid

        # Подготовка результатов с сохранением поля debt
        historical_data = []
        for i, (_, row) in enumerate(df.iterrows()):
            historical_data.append({
                'period': row['period'],
                'debt': float(row['monthly_debt']),  # сохраняем старое поле
                'monthly_debt': float(row['monthly_debt']),  # добавляем новое
                'cumulative_debt': float(historical_cumulative[i])
            })

        forecast_data = []
        for i, period in enumerate(future_dates):
            forecast_data.append({
                'period': period,
                'debt': float(y_pred[i]),  # сохраняем старое поле
                'monthly_debt': float(y_pred[i]),  # добавляем новое
                'cumulative_debt': float(forecast_cumulative[i]),
                'lower_bound': float(lower_bound[i]),
                'upper_bound': float(upper_bound[i])
            })

        return {
            'historical': historical_data,
            'forecast': forecast_data,
            'accuracy_metrics': {
                'mae': round(float(mae), 2),
                'rmse': round(float(rmse), 2),
                'r_squared': round(float(r_squared), 4)
            },
            'model_info': 'Линейная регрессия с ограничениями',
            'forecast_months': months,
            'has_confidence': True
        }