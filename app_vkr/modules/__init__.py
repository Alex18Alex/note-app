"""
Модули для анализа задолженностей по ЖКУ

Этот пакет содержит следующие модули:
- data_processor: Обработка и валидация входных данных
- analyzer: Расчет KPI и аналитика данных
- forecaster: Прогнозирование задолженностей
- visualizer: Визуализация данных и создание графиков
"""

from .data_processor import DataProcessor
from .analyzer import DebtAnalyzer
from .forecaster import DebtForecaster
from .visualizer import DataVisualizer

__all__ = ['DataProcessor', 'DebtAnalyzer', 'DebtForecaster', 'DataVisualizer']
__version__ = '1.0.0'
__author__ = 'JKHU Analytics Team'

print("Модули анализа ЖКУ успешно загружены")