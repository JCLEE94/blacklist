// Dashboard Charts Module
console.log('Loading dashboard-charts.js...');

// Wait for Chart.js to be loaded
window.addEventListener('load', function() {
    console.log('Window loaded, initializing charts...');
    
    // Initialize monthly trend chart
    initializeMonthlyChart();
    
    // Initialize source distribution chart
    initializeSourceChart();
    
    // Load data
    loadDashboardData();
});

function initializeMonthlyChart() {
    const canvas = document.getElementById('monthlyChart');
    if (!canvas) {
        console.error('Monthly chart canvas not found');
        return;
    }
    
    console.log('Creating monthly chart...');
    
    const ctx = canvas.getContext('2d');
    window.monthlyChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['2월', '3월', '4월', '5월', '6월', '7월'],
            datasets: [{
                label: 'REGTECH',
                data: [0, 0, 0, 0, 0, 22216],
                borderColor: '#5046e5',
                backgroundColor: 'rgba(80, 70, 229, 0.1)',
                borderWidth: 3,
                tension: 0.4,
                fill: true
            }, {
                label: 'SECUDIUM',
                data: [0, 0, 0, 0, 0, 466],
                borderColor: '#10b981',
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                borderWidth: 3,
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    }
                },
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return value.toLocaleString();
                        }
                    }
                }
            }
        }
    });
    
    console.log('Monthly chart created');
}

function initializeSourceChart() {
    const canvas = document.getElementById('sourceChart');
    if (!canvas) {
        console.error('Source chart canvas not found');
        return;
    }
    
    console.log('Creating source chart...');
    
    const ctx = canvas.getContext('2d');
    window.sourceChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['REGTECH', 'SECUDIUM', 'Public'],
            datasets: [{
                data: [22216, 466, 0],
                backgroundColor: [
                    '#5046e5',
                    '#10b981',
                    '#f59e0b'
                ],
                borderWidth: 0,
                hoverOffset: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '70%',
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = Math.round((context.raw / total) * 100);
                            return context.label + ': ' + context.raw.toLocaleString() + '개 (' + percentage + '%)';
                        }
                    }
                }
            }
        }
    });
    
    console.log('Source chart created');
}

async function loadDashboardData() {
    try {
        // Load monthly data
        const monthlyResponse = await fetch('/api/stats/monthly');
        const monthlyResult = await monthlyResponse.json();
        
        if (monthlyResult.success && window.monthlyChart) {
            const data = monthlyResult.data;
            
            // Update chart data
            window.monthlyChart.data.labels = data.map(d => {
                const [year, month] = d.month.split('-');
                return parseInt(month) + '월';
            });
            
            window.monthlyChart.data.datasets[0].data = data.map(d => d.regtech || 0);
            window.monthlyChart.data.datasets[1].data = data.map(d => d.secudium || 0);
            
            window.monthlyChart.update();
            console.log('Monthly chart updated with data');
        }
        
        // Load stats for source distribution
        const statsResponse = await fetch('/api/stats');
        const statsResult = await statsResponse.json();
        
        if (statsResult.success && statsResult.data && window.sourceChart) {
            const stats = statsResult.data;
            const total = stats.total_ips || 1;
            
            window.sourceChart.data.datasets[0].data = [
                stats.regtech_count || 0,
                stats.secudium_count || 0,
                stats.public_count || 0
            ];
            
            window.sourceChart.update();
            console.log('Source chart updated with data');
            
            // Update percentage display
            updateSourcePercentages(stats);
        }
    } catch (error) {
        console.error('Error loading dashboard data:', error);
    }
}

function updateSourcePercentages(stats) {
    const total = stats.total_ips || 1;
    
    const regtechPct = Math.round((stats.regtech_count / total) * 100);
    const secudiumPct = Math.round((stats.secudium_count / total) * 100);
    const publicPct = Math.round(((stats.public_count || 0) / total) * 100);
    
    // Find and update the percentage displays
    const percentageElements = document.querySelectorAll('.col-lg-4 .card-body .d-flex');
    percentageElements.forEach((el, idx) => {
        const spans = el.querySelectorAll('span');
        if (spans.length >= 2) {
            if (idx === 0) {
                spans[0].innerHTML = `REGTECH (${stats.regtech_count}개)`;
                spans[1].textContent = `${regtechPct}%`;
            } else if (idx === 1) {
                spans[0].innerHTML = `SECUDIUM (${stats.secudium_count}개)`;
                spans[1].textContent = `${secudiumPct}%`;
            } else if (idx === 2) {
                spans[0].innerHTML = `Public Sources (${stats.public_count || 0}개)`;
                spans[1].textContent = `${publicPct}%`;
            }
        }
    });
}