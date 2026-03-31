// Глобальные переменные
let dynamicsChart = null;
let serviceChart = null;
let agingChart = null;
let riskChart = null;

// Инициализация
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded');
    loadDatasets();
    setupFileUpload();
});

// Загрузка списка датасетов
async function loadDatasets() {
    try {
        const response = await fetch('/api/datasets');
        const datasets = await response.json();
        const select = document.getElementById('datasetSelect');
        if (!select) return;

        select.innerHTML = '<option value="">Выберите датасет...</option>';
        datasets.forEach(dataset => {
            const option = document.createElement('option');
            option.value = dataset.id;
            option.textContent = `${dataset.name} (${new Date(dataset.upload_date).toLocaleDateString()})`;
            select.appendChild(option);
        });

        const urlParams = new URLSearchParams(window.location.search);
        const datasetId = urlParams.get('dataset_id');
        if (datasetId) {
            select.value = datasetId;
            loadAnalyticsData(datasetId);
        }

        select.addEventListener('change', function() {
            if (this.value) loadAnalyticsData(this.value);
        });
    } catch (error) {
        console.error('Error loading datasets:', error);
    }
}

// Загрузка данных аналитики
async function loadAnalyticsData(datasetId) {
    console.log('Loading dataset:', datasetId);

    try {
        // Загружаем основные данные
        const response = await fetch(`/api/analytics/${datasetId}`);
        const data = await response.json();

        updateKPICards(data.kpi);
        updateDebtorsTable(data.charts.debtors_data);

        // Обновляем основные графики
        updateDynamicsChart(data.charts.dynamic_data);
        updateServiceChart(data.charts.service_data);

        // Загружаем дополнительные данные
        await loadDebtAgingData(datasetId);
        await loadDebtorClassificationData(datasetId);

    } catch (error) {
        console.error('Error loading analytics:', error);
    }
}

// Загрузка возрастной структуры
async function loadDebtAgingData(datasetId) {
    try {
        const response = await fetch(`/api/debt-aging?dataset_id=${datasetId}`);
        const agingData = await response.json();

        const canvas = document.getElementById('agingChart');
        if (!canvas) {
            console.error('Canvas agingChart not found');
            return;
        }

        const ctx = canvas.getContext('2d');

        // Уничтожаем старый график
        if (agingChart) {
            agingChart.destroy();
            agingChart = null;
        }

        // Очищаем canvas
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Создаем новый график
        agingChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: Object.keys(agingData),
                datasets: [{
                    label: 'Сумма задолженности (руб.)',
                    data: Object.values(agingData),
                    backgroundColor: ['#28a745', '#ffc107', '#fd7e14', '#dc3545']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return value.toLocaleString() + ' ₽';
                            }
                        }
                    }
                }
            }
        });
        console.log('Aging chart created');

    } catch(e) {
        console.error('Aging error:', e);
    }
}

// Загрузка классификации должников
async function loadDebtorClassificationData(datasetId) {
    try {
        const response = await fetch(`/api/debtor-classification?dataset_id=${datasetId}`);
        const riskData = await response.json();

        const canvas = document.getElementById('riskChart');
        if (!canvas) {
            console.error('Canvas riskChart not found');
            return;
        }

        const ctx = canvas.getContext('2d');

        // Уничтожаем старый график
        if (riskChart) {
            riskChart.destroy();
            riskChart = null;
        }

        // Очищаем canvas
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        if (riskData.statistics && Object.keys(riskData.statistics.by_risk).length > 0) {
            const labels = Object.keys(riskData.statistics.by_risk);
            const values = Object.values(riskData.statistics.by_risk);
            const colors = {
                'Критический': '#dc3545',
                'Высокий': '#fd7e14',
                'Средний': '#ffc107',
                'Низкий': '#28a745',
                'Минимальный': '#17a2b8'
            };

            riskChart = new Chart(ctx, {
                type: 'pie',
                data: {
                    labels: labels,
                    datasets: [{
                        data: values,
                        backgroundColor: labels.map(l => colors[l] || '#6c757d')
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: false,
                    plugins: {
                        legend: { position: 'bottom' }
                    }
                }
            });
            console.log('Risk chart created');
        }
    } catch(e) {
        console.error('Risk error:', e);
    }
}

// Обновление KPI карточек
function updateKPICards(kpi) {
    const totalDebt = document.getElementById('total-debt');
    const avgDebt = document.getElementById('avg-debt');
    const debtorsPct = document.getElementById('debtors-pct');
    const collectionRate = document.getElementById('collection-rate');

    if (totalDebt) totalDebt.textContent = formatCurrency(kpi.total_debt);
    if (avgDebt) avgDebt.textContent = formatCurrency(kpi.avg_debt_per_account);
    if (debtorsPct) debtorsPct.textContent = kpi.debtors_percentage + '%';
    if (collectionRate) collectionRate.textContent = kpi.collection_rate + '%';
}

// График динамики
function updateDynamicsChart(data) {
    const canvas = document.getElementById('dynamicsChart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');

    if (dynamicsChart) {
        dynamicsChart.destroy();
        dynamicsChart = null;
    }

    dynamicsChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.periods,
            datasets: [
                {
                    label: 'Начисления',
                    data: data.charges,
                    borderColor: 'rgb(54, 162, 235)',
                    backgroundColor: 'rgba(54, 162, 235, 0.1)',
                    fill: false,
                    tension: 0.1
                },
                {
                    label: 'Платежи',
                    data: data.payments,
                    borderColor: 'rgb(75, 192, 192)',
                    backgroundColor: 'rgba(75, 192, 192, 0.1)',
                    fill: false,
                    tension: 0.1
                },
                {
                    label: 'Задолженность',
                    data: data.debts,
                    borderColor: 'rgb(255, 99, 132)',
                    backgroundColor: 'rgba(255, 99, 132, 0.1)',
                    fill: false,
                    tension: 0.1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            plugins: {
                title: { display: true, text: 'Динамика начислений, платежей и задолженностей' }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { callback: function(value) { return formatCurrency(value); } }
                }
            }
        }
    });
}

// Круговая диаграмма услуг
function updateServiceChart(data) {
    const canvas = document.getElementById('serviceChart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');

    if (serviceChart) {
        serviceChart.destroy();
        serviceChart = null;
    }

    serviceChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.services,
            datasets: [{
                data: data.debts,
                backgroundColor: ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40']
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            plugins: {
                legend: { position: 'bottom' }
            }
        }
    });
}

// Обновление таблицы должников
function updateDebtorsTable(debtorsData) {
    const tbody = document.querySelector('#debtorsTable tbody');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (!debtorsData || debtorsData.length === 0) {
        tbody.innerHTML = '苦<td colspan="4" class="text-center">Нет данных о должниках</td></tr>';
        return;
    }

    debtorsData.forEach(debtor => {
        tbody.innerHTML += `
            <tr>
                <td>${debtor.account_id}</td>
                <td>${debtor.resident_name || '-'}</td>
                <td>${debtor.address || '-'}</td>
                <td class="text-danger fw-bold">${formatCurrency(debtor.total_debt)}</td>
            </tr>
        `;
    });
}

// Форматирование валюты
function formatCurrency(amount) {
    return new Intl.NumberFormat('ru-RU', {
        style: 'currency',
        currency: 'RUB',
        minimumFractionDigits: 0
    }).format(amount);
}

// Обработка загрузки файлов
function setupFileUpload() {
    const fileInput = document.getElementById('fileInput');
    const uploadArea = document.getElementById('uploadArea');

    if (uploadArea) {
        uploadArea.addEventListener('click', () => fileInput.click());
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            if (e.dataTransfer.files.length) {
                fileInput.files = e.dataTransfer.files;
                handleFileUpload();
            }
        });
    }

    if (fileInput) {
        fileInput.addEventListener('change', handleFileUpload);
    }
}

// Обработка загрузки файла
async function handleFileUpload() {
    const fileInput = document.getElementById('fileInput');
    const submitBtn = document.getElementById('submitBtn');
    const statusDiv = document.getElementById('uploadStatus');

    if (!fileInput.files.length) return;

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Загрузка...';
    }
    if (statusDiv) {
        statusDiv.innerHTML = '<div class="alert alert-info">Загрузка файла...</div>';
    }

    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (result.success) {
            if (statusDiv) {
                statusDiv.innerHTML = `<div class="alert alert-success">${result.message}</div>`;
            }
            setTimeout(() => {
                window.location.href = `/analytics?dataset_id=${result.dataset_id}`;
            }, 2000);
        } else {
            if (statusDiv) {
                statusDiv.innerHTML = `<div class="alert alert-danger">Ошибка: ${result.message || result.errors?.join(', ')}</div>`;
            }
        }
    } catch (error) {
        if (statusDiv) {
            statusDiv.innerHTML = `<div class="alert alert-danger">Ошибка сети: ${error.message}</div>`;
        }
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Загрузить данные';
        }
    }
}