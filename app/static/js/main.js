document.addEventListener("DOMContentLoaded", function () {
    if (!window.solarChartData || window.solarChartData.length === 0) {
        return;
    }

    const ctx = document.getElementById('solarChart').getContext('2d');
    
    // Extrair labels (datas) e valores (gerado real e estimado)
    const labels = window.solarChartData.map(item => item.data);
    const dataReal = window.solarChartData.map(item => item.real);
    const dataEstimado = window.solarChartData.map(item => item.estimado);

    // Gradientes para preenchimento de área sob as curvas
    const gradientReal = ctx.createLinearGradient(0, 0, 0, 300);
    gradientReal.addColorStop(0, 'rgba(42, 203, 120, 0.15)');
    gradientReal.addColorStop(1, 'rgba(42, 203, 120, 0.01)');

    const gradientEstimado = ctx.createLinearGradient(0, 0, 0, 300);
    gradientEstimado.addColorStop(0, 'rgba(43, 177, 219, 0.08)');
    gradientEstimado.addColorStop(1, 'rgba(43, 177, 219, 0.01)');

    const chartConfig = {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Geração Real (kWh)',
                    data: dataReal,
                    borderColor: '#2acb78',
                    backgroundColor: gradientReal,
                    borderWidth: 3,
                    pointBackgroundColor: '#2acb78',
                    pointBorderColor: '#152030',
                    pointBorderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    fill: true,
                    tension: 0.3
                },
                {
                    label: 'Geração Estimada (kWh)',
                    data: dataEstimado,
                    borderColor: '#2bb1db',
                    backgroundColor: gradientEstimado,
                    borderWidth: 3,
                    borderDash: [5, 5],
                    pointBackgroundColor: '#2bb1db',
                    pointBorderColor: '#152030',
                    pointBorderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    fill: true,
                    tension: 0.3
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        color: '#f8fafc',
                        font: {
                            family: "'Inter', sans-serif",
                            size: 11,
                            weight: '500'
                        },
                        boxWidth: 15,
                        padding: 15
                    }
                },
                tooltip: {
                    backgroundColor: '#152030',
                    titleColor: '#f8fafc',
                    titleFont: {
                        family: "'Outfit', sans-serif",
                        weight: '700'
                    },
                    bodyColor: '#94a3b8',
                    bodyFont: {
                        family: "'Inter', sans-serif"
                    },
                    borderColor: '#1e293b',
                    borderWidth: 1,
                    padding: 12,
                    cornerRadius: 8,
                    displayColors: true,
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.parsed.y !== null) {
                                label += context.parsed.y.toFixed(2) + ' kWh';
                            }
                            return label;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        color: '#1e293b',
                        drawBorder: false
                    },
                    ticks: {
                        color: '#94a3b8',
                        font: {
                            family: "'Inter', sans-serif', size: 10"
                        },
                        maxRotation: 45,
                        minRotation: 0
                    }
                },
                y: {
                    grid: {
                        color: '#1e293b',
                        drawBorder: false
                    },
                    ticks: {
                        color: '#94a3b8',
                        font: {
                            family: "'Inter', sans-serif', size: 10"
                        },
                        callback: function(value) {
                            return value + ' kWh';
                        }
                    }
                }
            }
        }
    };

    new Chart(ctx, chartConfig);
});
