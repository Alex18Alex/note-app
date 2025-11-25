// Загрузка данных аналитики
async function loadAnalyticsData(datasetId) {
    try {
        const response = await fetch(`/api/analytics/${datasetId}`);
        const data = await response.json();

        updateKPICards(data.kpi);
        createCharts(data.charts);
        updateDebtorsTable(data.charts.debtors_data);

    } catch (error) {
        console.error('Error loading analytics data:', error);
        alert('Ошибка при загрузке данных аналитики');
    }
}

// Обновление KPI карточек
function updateKPICards(kpi) {
    document.getElementById('total-debt').textContent = formatCurrency(kpi.total_debt);
    document.getElementById('avg-debt').textContent = formatCurrency(kpi.avg_debt_per_account);
    document.getElementById('debtors-pct').textContent = kpi.debtors_percentage + '%';
    document.getElementById('collection-rate').textContent = kpi.collection_rate + '%';
}

// Создание графиков
function createCharts(chartsData) {
    createDynamicsChart(chartsData.dynamic_data);
    createServiceChart(chartsData.service_data);
}

// График динамики
function createDynamicsChart(data) {
    const ctx = document.getElementById('dynamicsChart').getContext('2d');
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.periods,
            datasets: [
                {
                    label: 'Начисления',
                    data: data.charges,
                    borderColor: 'rgb(54, 162, 235)',
                    backgroundColor: 'rgba(54, 162, 235, 0.1)',
                    tension: 0.1
                },
                {
                    label: 'Платежи',
                    data: data.payments,
                    borderColor: 'rgb(75, 192, 192)',
                    backgroundColor: 'rgba(75, 192, 192, 0.1)',
                    tension: 0.1
                },
                {
                    label: 'Задолженность',
                    data: data.debts,
                    borderColor: 'rgb(255, 99, 132)',
                    backgroundColor: 'rgba(255, 99, 132, 0.1)',
                    tension: 0.1
                }
            ]
        },
        options: {
            responsive: true,
            plugins: {
                title: {
                    display: true,
                    text: 'Динамика начислений, платежей и задолженностей'
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return formatCurrency(value);
                        }
                    }
                }
            }
        }
    });
}

// Круговая диаграмма услуг
function createServiceChart(data) {
    const ctx = document.getElementById('serviceChart').getContext('2d');
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.services,
            datasets: [{
                data: data.debts,
                backgroundColor: [
                    '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0',
                    '#9966FF', '#FF9F40', '#FF6384', '#C9CBCF'
                ]
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const value = context.raw;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = Math.round((value / total) * 100);
                            return `${context.label}: ${formatCurrency(value)} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

// Обновление таблицы должников
function updateDebtorsTable(debtorsData) {
    const tbody = document.querySelector('#debtorsTable tbody');
    tbody.innerHTML = '';

    debtorsData.forEach(debtor => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${debtor.account_id}</td>
            <td>${debtor.resident_name}</td>
            <td>${debtor.address}</td>
            <td class="text-danger fw-bold">${formatCurrency(debtor.total_debt)}</td>
        `;
        tbody.appendChild(row);
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

    submitBtn.disabled = true;
    submitBtn.textContent = 'Загрузка...';
    statusDiv.innerHTML = '<div class="alert alert-info">Загрузка файла...</div>';

    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (result.success) {
            statusDiv.innerHTML = `<div class="alert alert-success">${result.message}</div>`;
            setTimeout(() => {
                window.location.href = `/analytics?dataset_id=${result.dataset_id}`;
            }, 2000);
        } else {
            statusDiv.innerHTML = `<div class="alert alert-danger">Ошибка: ${result.error}</div>`;
        }
    } catch (error) {
        statusDiv.innerHTML = `<div class="alert alert-danger">Ошибка сети: ${error.message}</div>`;
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Загрузить данные';
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    setupFileUpload();
});