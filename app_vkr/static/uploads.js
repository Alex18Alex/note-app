// static/js/upload.js

document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.getElementById('uploadForm');
    if (!uploadForm) return;

    const loadingSpinner = document.getElementById('loadingSpinner');

    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const fileInput = document.getElementById('file');

        // Проверка файла
        if (!fileInput.files || fileInput.files.length === 0) {
            showWarning('Файл не выбран', 'Пожалуйста, выберите файл для загрузки');
            return;
        }

        const file = fileInput.files[0];
        const fileExt = file.name.split('.').pop().toLowerCase();

        // Проверка формата
        if (!['csv', 'xlsx', 'xls'].includes(fileExt)) {
            showError('Неверный формат файла', 'Поддерживаются только CSV и Excel файлы');
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        // Показываем спиннер
        if (loadingSpinner) loadingSpinner.style.display = 'block';

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            // Скрываем спиннер
            if (loadingSpinner) loadingSpinner.style.display = 'none';

            if (result.success) {
                showSuccess(result);
            } else {
                showValidationErrors(result);
            }

        } catch (error) {
            // Скрываем спиннер
            if (loadingSpinner) loadingSpinner.style.display = 'none';

            console.error('Upload error:', error);
            showError('Ошибка соединения', 'Не удалось连接到 серверу. Проверьте подключение.');
        }
    });
});

function showSuccess(result) {
    let html = `<p style="font-size: 1.1em;">✅ ${result.message}</p>`;

    if (result.warnings && result.warnings.length > 0) {
        html += '<br><b style="color: #856404;">⚠️ Предупреждения:</b><ul style="text-align: left;">';
        result.warnings.forEach(w => {
            html += `<li style="color: #856404;">${w}</li>`;
        });
        html += '</ul>';
    }

    html += `<p style="margin-top: 10px;">📊 Загружено записей: <b>${result.records_processed}</b></p>`;

    Swal.fire({
        icon: 'success',
        title: 'Файл успешно загружен!',
        html: html,
        confirmButtonColor: '#28a745',
        confirmButtonText: 'Перейти к анализу'
    }).then((result) => {
        if (result.isConfirmed) {
            window.location.href = `/dashboard?dataset_id=${result.dataset_id}`;
        }
    });
}

function showValidationErrors(result) {
    let errorsHtml = '<div style="text-align: left; max-height: 300px; overflow-y: auto;">';

    if (result.errors && result.errors.length > 0) {
        result.errors.forEach(error => {
            // Подсвечиваем разные типы ошибок разными цветами
            if (error.includes('отрицательн')) {
                errorsHtml += `
                    <div style="background: #f8d7da; border-left: 4px solid #dc3545; padding: 10px; margin-bottom: 10px; border-radius: 4px;">
                        <span style="color: #721c24;">💰 ${error}</span>
                    </div>
                `;
            } else if (error.includes('пропущен')) {
                errorsHtml += `
                    <div style="background: #fff3cd; border-left: 4px solid #ffc107; padding: 10px; margin-bottom: 10px; border-radius: 4px;">
                        <span style="color: #856404;">📝 ${error}</span>
                    </div>
                `;
            } else if (error.includes('формат')) {
                errorsHtml += `
                    <div style="background: #d1ecf1; border-left: 4px solid #17a2b8; padding: 10px; margin-bottom: 10px; border-radius: 4px;">
                        <span style="color: #0c5460;">📅 ${error}</span>
                    </div>
                `;
            } else {
                errorsHtml += `
                    <div style="background: #f8d7da; border-left: 4px solid #dc3545; padding: 10px; margin-bottom: 10px; border-radius: 4px;">
                        <span style="color: #721c24;">❌ ${error}</span>
                    </div>
                `;
            }
        });
    } else {
        errorsHtml += `<p style="color: #721c24;">${result.message || 'Неизвестная ошибка'}</p>`;
    }

    errorsHtml += '</div>';

    Swal.fire({
        icon: 'error',
        title: 'Ошибка загрузки файла',
        html: `
            ${errorsHtml}
            <hr>
            <div style="background: #e2e3e5; padding: 15px; border-radius: 5px; text-align: left; margin-top: 15px;">
                <b style="color: #383d41;">📋 Требования к файлу:</b>
                <ul style="margin-top: 8px; margin-bottom: 5px; color: #383d41;">
                    <li><b>Обязательные колонки:</b> account_id, period, charge_amount, payment_amount</li>
                    <li><b>Суммы:</b> должны быть ≥ 0 (без отрицательных значений)</li>
                    <li><b>Период:</b> формат ГГГГ-ММ (например, 2024-01)</li>
                    <li><b>Пропуски:</b> не должно быть пустых значений в обязательных полях</li>
                </ul>
            </div>
        `,
        confirmButtonColor: '#dc3545',
        confirmButtonText: 'Понятно, исправлю файл'
    });
}

function showError(title, message) {
    Swal.fire({
        icon: 'error',
        title: title,
        text: message,
        confirmButtonColor: '#dc3545'
    });
}

function showWarning(title, message) {
    Swal.fire({
        icon: 'warning',
        title: title,
        text: message,
        confirmButtonColor: '#ffc107'
    });
}