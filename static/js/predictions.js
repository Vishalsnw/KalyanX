/**
 * KalyanX - Predictions JS
 * Handles prediction-related functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    // Date selector for predictions page
    const dateSelector = document.getElementById('date-selector');
    if (dateSelector) {
        dateSelector.addEventListener('change', function() {
            const url = new URL(window.location.href);
            url.searchParams.set('date', this.value);
            window.location.href = url.toString();
        });
    }
    
    // Market selector for predictions page
    const marketSelector = document.getElementById('market-selector');
    if (marketSelector) {
        marketSelector.addEventListener('change', function() {
            const url = new URL(window.location.href);
            if (this.value) {
                url.searchParams.set('market', this.value);
            } else {
                url.searchParams.delete('market');
            }
            window.location.href = url.toString();
        });
    }
    
    // Refresh predictions button (admin only)
    const refreshPredictionsBtn = document.querySelectorAll('.refresh-predictions-btn');
    refreshPredictionsBtn.forEach(btn => {
        btn.addEventListener('click', function() {
            const market = this.getAttribute('data-market');
            refreshPredictions(market, this);
        });
    });
    
    // Copy jodi to clipboard
    const copyJodiButtons = document.querySelectorAll('.copy-jodi-btn');
    copyJodiButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const jodi = this.getAttribute('data-jodi');
            copyToClipboard(jodi)
                .then(() => {
                    const originalText = this.innerHTML;
                    this.innerHTML = '<i class="fas fa-check"></i> Copied!';
                    setTimeout(() => {
                        this.innerHTML = originalText;
                    }, 2000);
                })
                .catch(() => {
                    showToast('Error', 'Failed to copy jodi', 'danger');
                });
        });
    });
    
    // Setup animated counters for statistics
    setupAnimatedCounters();
    
    // Initialize charts if they exist
    initializeCharts();
});

/**
 * Refresh predictions for a specific market
 * @param {string} market - The market to refresh predictions for
 * @param {HTMLElement} button - The button that triggered the refresh
 */
function refreshPredictions(market, button) {
    // Show loading state
    const originalHtml = button.innerHTML;
    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Refreshing...';
    button.disabled = true;
    
    fetch(`/api/update-predictions/${market}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('Success', data.message, 'success');
            
            // Reload the page to show new predictions
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } else {
            showToast('Error', data.message, 'danger');
            // Reset button
            button.innerHTML = originalHtml;
            button.disabled = false;
        }
    })
    .catch(error => {
        console.error('Error refreshing predictions:', error);
        showToast('Error', 'Failed to refresh predictions', 'danger');
        // Reset button
        button.innerHTML = originalHtml;
        button.disabled = false;
    });
}

/**
 * Setup animated counters for statistics
 */
function setupAnimatedCounters() {
    const counters = document.querySelectorAll('.counter-value');
    
    counters.forEach(counter => {
        const target = parseInt(counter.getAttribute('data-count'));
        const duration = 1500; // milliseconds
        const step = Math.ceil(target / (duration / 16)); // 60fps
        
        let current = 0;
        const timer = setInterval(() => {
            current += step;
            if (current >= target) {
                current = target;
                clearInterval(timer);
            }
            counter.textContent = current.toLocaleString();
        }, 16);
    });
}

/**
 * Initialize charts for data visualization
 */
function initializeCharts() {
    // Prediction accuracy chart
    const accuracyChartElement = document.getElementById('prediction-accuracy-chart');
    if (accuracyChartElement) {
        const markets = JSON.parse(accuracyChartElement.getAttribute('data-markets') || '[]');
        const openData = JSON.parse(accuracyChartElement.getAttribute('data-open') || '[]');
        const closeData = JSON.parse(accuracyChartElement.getAttribute('data-close') || '[]');
        const jodiData = JSON.parse(accuracyChartElement.getAttribute('data-jodi') || '[]');
        
        createPredictionAccuracyChart(accuracyChartElement, markets, openData, closeData, jodiData);
    }
    
    // Results trend chart
    const resultsTrendElement = document.getElementById('results-trend-chart');
    if (resultsTrendElement) {
        const dates = JSON.parse(resultsTrendElement.getAttribute('data-dates') || '[]');
        const jodiValues = JSON.parse(resultsTrendElement.getAttribute('data-jodi-values') || '[]');
        
        createResultsTrendChart(resultsTrendElement, dates, jodiValues);
    }
    
    // Market distribution chart
    const marketDistributionElement = document.getElementById('market-distribution-chart');
    if (marketDistributionElement) {
        const markets = JSON.parse(marketDistributionElement.getAttribute('data-markets') || '[]');
        const counts = JSON.parse(marketDistributionElement.getAttribute('data-counts') || '[]');
        
        createMarketDistributionChart(marketDistributionElement, markets, counts);
    }
}

/**
 * Create prediction accuracy chart
 * @param {HTMLElement} element - The canvas element
 * @param {Array} markets - Array of market names
 * @param {Array} openData - Open prediction accuracy data
 * @param {Array} closeData - Close prediction accuracy data
 * @param {Array} jodiData - Jodi prediction accuracy data
 */
function createPredictionAccuracyChart(element, markets, openData, closeData, jodiData) {
    const ctx = element.getContext('2d');
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: markets,
            datasets: [
                {
                    label: 'Open Accuracy',
                    data: openData,
                    backgroundColor: 'rgba(13, 202, 240, 0.6)',
                    borderColor: 'rgba(13, 202, 240, 1)',
                    borderWidth: 1
                },
                {
                    label: 'Close Accuracy',
                    data: closeData,
                    backgroundColor: 'rgba(25, 135, 84, 0.6)',
                    borderColor: 'rgba(25, 135, 84, 1)',
                    borderWidth: 1
                },
                {
                    label: 'Jodi Accuracy',
                    data: jodiData,
                    backgroundColor: 'rgba(220, 53, 69, 0.6)',
                    borderColor: 'rgba(220, 53, 69, 1)',
                    borderWidth: 1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    title: {
                        display: true,
                        text: 'Accuracy (%)'
                    }
                }
            },
            plugins: {
                legend: {
                    position: 'top',
                },
                title: {
                    display: true,
                    text: 'Prediction Accuracy by Market'
                }
            }
        }
    });
}

/**
 * Create results trend chart
 * @param {HTMLElement} element - The canvas element
 * @param {Array} dates - Array of dates
 * @param {Array} jodiValues - Array of jodi values
 */
function createResultsTrendChart(element, dates, jodiValues) {
    const ctx = element.getContext('2d');
    
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [
                {
                    label: 'Jodi Values',
                    data: jodiValues,
                    backgroundColor: 'rgba(255, 193, 7, 0.2)',
                    borderColor: 'rgba(255, 193, 7, 1)',
                    borderWidth: 2,
                    tension: 0.4,
                    pointRadius: 4,
                    pointBackgroundColor: 'rgba(255, 193, 7, 1)'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Jodi Value'
                    }
                }
            },
            plugins: {
                legend: {
                    position: 'top',
                },
                title: {
                    display: true,
                    text: 'Jodi Value Trend'
                }
            }
        }
    });
}

/**
 * Create market distribution chart
 * @param {HTMLElement} element - The canvas element
 * @param {Array} markets - Array of market names
 * @param {Array} counts - Array of result counts
 */
function createMarketDistributionChart(element, markets, counts) {
    const ctx = element.getContext('2d');
    
    // Generate colors for each market
    const colors = markets.map((_, index) => {
        const hue = (index * 360 / markets.length) % 360;
        return `hsl(${hue}, 70%, 60%)`;
    });
    
    new Chart(ctx, {
        type: 'pie',
        data: {
            labels: markets,
            datasets: [
                {
                    data: counts,
                    backgroundColor: colors,
                    borderColor: '#212529',
                    borderWidth: 1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                },
                title: {
                    display: true,
                    text: 'Results by Market'
                }
            }
        }
    });
}
