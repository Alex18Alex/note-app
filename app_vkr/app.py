from flask import Flask, render_template, request, jsonify, send_file
import os
import sqlite3
import pandas as pd
from datetime import datetime
import json

from modules.data_processor import DataProcessor
from modules.analyzer import DebtAnalyzer
from modules.forecaster import DebtForecaster
from modules.visualizer import DataVisualizer

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['DATABASE'] = 'database/jkhu.db'


# Инициализация базы данных
def init_database():
    os.makedirs('database', exist_ok=True)
    conn = sqlite3.connect(app.config['DATABASE'])
    cursor = conn.cursor()

    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS datasets
                   (
                       id
                       INTEGER
                       PRIMARY
                       KEY
                       AUTOINCREMENT,
                       name
                       TEXT
                       NOT
                       NULL,
                       upload_date
                       TIMESTAMP
                       DEFAULT
                       CURRENT_TIMESTAMP,
                       description
                       TEXT
                   )
                   ''')

    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS payment_records
                   (
                       id
                       INTEGER
                       PRIMARY
                       KEY
                       AUTOINCREMENT,
                       dataset_id
                       INTEGER,
                       account_id
                       TEXT,
                       address
                       TEXT,
                       resident_name
                       TEXT,
                       period
                       TEXT,
                       service_type
                       TEXT,
                       charge_amount
                       REAL,
                       payment_amount
                       REAL,
                       FOREIGN
                       KEY
                   (
                       dataset_id
                   ) REFERENCES datasets
                   (
                       id
                   )
                       )
                   ''')

    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS analysis_results
                   (
                       id
                       INTEGER
                       PRIMARY
                       KEY
                       AUTOINCREMENT,
                       dataset_id
                       INTEGER,
                       analysis_date
                       TIMESTAMP
                       DEFAULT
                       CURRENT_TIMESTAMP,
                       kpi_data
                       TEXT,
                       forecast_data
                       TEXT,
                       FOREIGN
                       KEY
                   (
                       dataset_id
                   ) REFERENCES datasets
                   (
                       id
                   )
                       )
                   ''')

    conn.commit()
    conn.close()


init_database()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['GET', 'POST'])
def upload_data():
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if file and file.filename.endswith(('.csv', '.xlsx')):
            try:
                processor = DataProcessor(app.config['DATABASE'])
                result = processor.process_uploaded_file(file)
                return jsonify(result)
            except Exception as e:
                return jsonify({'error': str(e)}), 500

    return render_template('upload.html')


@app.route('/analytics')
def analytics():
    dataset_id = request.args.get('dataset_id', 1, type=int)
    analyzer = DebtAnalyzer(app.config['DATABASE'])

    kpi_data = analyzer.calculate_kpi(dataset_id)
    charts_data = analyzer.get_charts_data(dataset_id)

    return render_template('analytics.html',
                           kpi_data=kpi_data,
                           charts_data=charts_data,
                           dataset_id=dataset_id)


@app.route('/api/analytics/<int:dataset_id>')
def api_analytics(dataset_id):
    analyzer = DebtAnalyzer(app.config['DATABASE'])
    kpi_data = analyzer.calculate_kpi(dataset_id)
    charts_data = analyzer.get_charts_data(dataset_id)

    return jsonify({
        'kpi': kpi_data,
        'charts': charts_data
    })


@app.route('/forecast', methods=['GET', 'POST'])
def forecast():
    dataset_id = request.args.get('dataset_id', 1, type=int)
    forecaster = DebtForecaster(app.config['DATABASE'])

    if request.method == 'POST':
        months = int(request.form.get('months', 6))
        forecast_data = forecaster.generate_forecast(dataset_id, months)
        return jsonify(forecast_data)

    return render_template('forecast.html', dataset_id=dataset_id)


@app.route('/api/datasets')
def get_datasets():
    conn = sqlite3.connect(app.config['DATABASE'])
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, upload_date FROM datasets ORDER BY upload_date DESC')
    datasets = cursor.fetchall()
    conn.close()

    return jsonify([{'id': row[0], 'name': row[1], 'upload_date': row[2]} for row in datasets])

@app.route('/api/system-stats')
def system_stats():
    conn = sqlite3.connect(app.config['DATABASE'])
    cursor = conn.cursor()

    # Количество датасетов
    cursor.execute('SELECT COUNT(*) FROM datasets')
    total_datasets = cursor.fetchone()[0]

    # Количество записей
    cursor.execute('SELECT COUNT(*) FROM payment_records')
    total_records = cursor.fetchone()[0]

    # Последнее обновление
    cursor.execute('SELECT MAX(upload_date) FROM datasets')
    last_update = cursor.fetchone()[0]

    conn.close()

    return jsonify({
        'total_datasets': total_datasets,
        'total_records': total_records,
        'last_update': last_update or 'Нет данных'
    })

if __name__ == '__main__':
    os.makedirs('uploads', exist_ok=True)
    app.run(debug=True, host='0.0.0.0', port=5001)