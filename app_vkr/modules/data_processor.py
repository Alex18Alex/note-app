import pandas as pd
import sqlite3
from datetime import datetime
import uuid
import os
import re


class DataValidationError(Exception):
    """Пользовательское исключение для ошибок валидации данных"""
    pass


class DataProcessor:
    def __init__(self, database_path):
        self.database_path = database_path
        self.required_columns = ['account_id','address', 'resident_name', 'period', 'service_type', 'charge_amount', 'payment_amount']
        self.numeric_columns = ['charge_amount', 'payment_amount']

    def process_uploaded_file(self, file):
        """Обрабатывает загруженный файл с данными с валидацией"""
        # Создаем директорию uploads, если её нет
        os.makedirs('uploads', exist_ok=True)

        # Сохраняем файл временно
        filename = f"upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
        filepath = os.path.join('uploads', filename)
        file.save(filepath)

        try:
            # Читаем файл в зависимости от формата
            if file.filename.endswith('.csv'):
                df = pd.read_csv(filepath, encoding='utf-8')
            elif file.filename.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(filepath)
            else:
                raise DataValidationError(f"Неподдерживаемый формат файла: {file.filename}. Используйте CSV или Excel.")

            # Валидация данных
            validation_result = self._validate_data(df)

            if not validation_result['is_valid']:
                # Если есть ошибки, не сохраняем в БД, а возвращаем информацию об ошибках
                return {
                    'success': False,
                    'errors': validation_result['errors'],
                    'warnings': validation_result['warnings'],
                    'message': 'Файл содержит ошибки. Пожалуйста, исправьте их и загрузите снова.'
                }

            # Сохраняем в базу данных только если данные валидны
            dataset_id = self._save_to_database(validation_result['data'], file.filename)

            # Удаляем временный файл
            os.remove(filepath)

            return {
                'success': True,
                'dataset_id': dataset_id,
                'records_processed': len(validation_result['data']),
                'message': f'✅ Успешно обработано {len(validation_result["data"])} записей',
                'warnings': validation_result['warnings']
            }

        except DataValidationError as e:
            # Ошибки валидации, которые нужно показать пользователю
            if os.path.exists(filepath):
                os.remove(filepath)
            return {
                'success': False,
                'errors': [str(e)],
                'message': str(e)
            }
        except Exception as e:
            # Непредвиденные ошибки
            if os.path.exists(filepath):
                os.remove(filepath)
            return {
                'success': False,
                'errors': [f'Ошибка при обработке файла: {str(e)}'],
                'message': 'Произошла внутренняя ошибка сервера'
            }

    def _validate_data(self, df):
        """
        Полная валидация данных с детальными сообщениями об ошибках
        Возвращает словарь с флагом is_valid, списком ошибок и предупреждений
        """
        errors = []
        warnings = []
        original_row_count = len(df)

        # 1. Проверка на пустой файл
        if df.empty:
            errors.append("❌ Файл не содержит данных")
            return {'is_valid': False, 'errors': errors, 'warnings': warnings, 'data': df}

        # 2. Проверка наличия обязательных колонок
        missing_columns = [col for col in self.required_columns if col not in df.columns]
        if missing_columns:
            errors.append(f"❌ Отсутствуют обязательные колонки: {', '.join(missing_columns)}")
            return {'is_valid': False, 'errors': errors, 'warnings': warnings, 'data': df}

        # 3. Проверка пропущенных значений в обязательных полях
        for col in self.required_columns:
            missing_count = df[col].isna().sum()
            if missing_count > 0:
                # Показываем примеры строк с пропусками
                missing_indices = df[df[col].isna()].index[:5].tolist()
                errors.append(
                    f"❌ В колонке '{col}' обнаружено {missing_count} пропущенных значений. "
                    f"Примеры строк: {missing_indices}"
                )

        # 4. Преобразование числовых колонок и проверка отрицательных значений
        for col in self.numeric_columns:
            if col in df.columns:
                # Пытаемся преобразовать в числовой тип
                try:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                except:
                    pass

                # Проверка на отрицательные значения
                negative_mask = df[col] < 0
                negative_count = negative_mask.sum()

                if negative_count > 0:
                    # Показываем примеры строк с ошибками
                    negative_indices = df[negative_mask].index[:5].tolist()
                    negative_values = df.loc[negative_indices, col].tolist()

                    example_text = ", ".join(
                        [f"строка {idx}: {val}" for idx, val in zip(negative_indices, negative_values)])
                    errors.append(
                        f"❌ В колонке '{col}' обнаружено {negative_count} отрицательных значений. "
                        f"Примеры: {example_text}"
                    )

        # 5. Проверка формата периода (должен быть ГГГГ-ММ)
        if 'period' in df.columns and 'period' not in missing_columns:
            invalid_periods = []
            invalid_period_values = []

            for idx, period in enumerate(df['period']):
                if pd.isna(period):
                    continue
                period_str = str(period).strip()
                # Проверяем формат YYYY-MM
                if not re.match(r'^\d{4}-\d{2}$', period_str):
                    invalid_periods.append(idx)
                    invalid_period_values.append(period_str[:20])  # Обрезаем длинные значения

            if invalid_periods:
                example_text = ", ".join(
                    [f"строка {idx}: '{val}'" for idx, val in zip(invalid_periods[:5], invalid_period_values[:5])])
                errors.append(
                    f"❌ Обнаружено {len(invalid_periods)} записей с неверным форматом периода. "
                    f"Ожидается формат ГГГГ-ММ (например, 2024-01). "
                    f"Примеры: {example_text}"
                )

        # Если есть ошибки, возвращаем их без дальнейшей обработки
        if errors:
            return {
                'is_valid': False,
                'errors': errors,
                'warnings': warnings,
                'data': df
            }

        # 6. Проверка дубликатов (предупреждение, а не ошибка)
        duplicate_check_cols = ['account_id', 'period', 'service_type'] if 'service_type' in df.columns else [
            'account_id', 'period']
        available_cols = [col for col in duplicate_check_cols if col in df.columns]

        if available_cols:
            duplicates = df.duplicated(subset=available_cols, keep=False)
            duplicate_count = duplicates.sum()

            if duplicate_count > 0:
                warnings.append(
                    f"⚠️ Обнаружено {duplicate_count} записей с одинаковыми "
                    f"{available_cols}. Убедитесь, что это разные услуги."
                )

        # 7. Проверка на слишком большие значения (предупреждение)
        for col in self.numeric_columns:
            if col in df.columns:
                huge_values = df[col] > 1000000
                huge_count = huge_values.sum()
                if huge_count > 0:
                    warnings.append(
                        f"⚠️ В колонке '{col}' обнаружено {huge_count} аномально больших значений (> 1 000 000). "
                        f"Проверьте корректность данных."
                    )

        # 8. Очистка данных (удаляем строки с пропущенными значениями в обязательных полях)
        initial_len = len(df)
        df = df.dropna(subset=self.required_columns)
        dropped_count = initial_len - len(df)

        if dropped_count > 0:
            warnings.append(f"⚠️ Удалено {dropped_count} строк с пропущенными значениями в обязательных полях")

        # 9. Преобразование числовых колонок и замена отрицательных на 0
        for col in self.numeric_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            # Заменяем отрицательные на 0 (на всякий случай, хотя мы уже проверили)
            df[col] = df[col].clip(lower=0)

        # 10. Финальная проверка: если после очистки не осталось данных
        if len(df) == 0:
            errors.append("❌ После очистки не осталось валидных данных для загрузки")
            return {'is_valid': False, 'errors': errors, 'warnings': warnings, 'data': df}

        return {
            'is_valid': True,
            'errors': [],
            'warnings': warnings,
            'data': df,
            'rows_removed': original_row_count - len(df)
        }

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
        records_saved = 0
        for _, row in df.iterrows():
            try:
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
                records_saved += 1
            except Exception as e:
                print(f"Ошибка при сохранении записи: {e}")
                # Продолжаем сохранять остальные записи

        conn.commit()
        conn.close()

        return dataset_id