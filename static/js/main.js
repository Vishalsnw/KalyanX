/**
 * KalyanX - Main JS File
 * Contains global functions used across the application
 */

// Initialize tooltips and popovers
document.addEventListener('DOMContentLoaded', function() {
    // Initialize all tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize all popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Handle mobile menu collapse
    const navLinks = document.querySelectorAll('.navbar-nav a.nav-link');
    const menuToggle = document.getElementById('navbarNav');
    const bsCollapse = new bootstrap.Collapse(menuToggle, {toggle: false});
    navLinks.forEach(function(link) {
        link.addEventListener('click', function() {
            if (window.innerWidth < 992 && menuToggle.classList.contains('show')) {
                bsCollapse.toggle();
            }
        });
    });
});

/**
 * Format date in DD/MM/YYYY format
 * @param {Date} date - The date to format
 * @returns {string} Formatted date string
 */
function formatDate(date) {
    const day = String(date.getDate()).padStart(2, '0');
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const year = date.getFullYear();
    return `${day}/${month}/${year}`;
}

/**
 * Format date and time in DD/MM/YYYY HH:MM format
 * @param {Date} date - The date to format
 * @returns {string} Formatted date and time string
 */
function formatDateTime(date) {
    const formattedDate = formatDate(date);
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    return `${formattedDate} ${hours}:${minutes}`;
}

/**
 * Format time elapsed since the given date
 * @param {string} dateString - The date string to calculate elapsed time from
 * @returns {string} Formatted elapsed time
 */
function timeAgo(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);
    
    let interval = Math.floor(seconds / 31536000);
    if (interval >= 1) {
        return interval + (interval === 1 ? " year ago" : " years ago");
    }
    
    interval = Math.floor(seconds / 2592000);
    if (interval >= 1) {
        return interval + (interval === 1 ? " month ago" : " months ago");
    }
    
    interval = Math.floor(seconds / 86400);
    if (interval >= 1) {
        return interval + (interval === 1 ? " day ago" : " days ago");
    }
    
    interval = Math.floor(seconds / 3600);
    if (interval >= 1) {
        return interval + (interval === 1 ? " hour ago" : " hours ago");
    }
    
    interval = Math.floor(seconds / 60);
    if (interval >= 1) {
        return interval + (interval === 1 ? " minute ago" : " minutes ago");
    }
    
    return Math.floor(seconds) + " seconds ago";
}

/**
 * Copy text to clipboard
 * @param {string} text - The text to copy
 * @returns {boolean} Success status
 */
function copyToClipboard(text) {
    if (!navigator.clipboard) {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        try {
            const successful = document.execCommand('copy');
            document.body.removeChild(textArea);
            return successful;
        } catch (err) {
            document.body.removeChild(textArea);
            console.error('Failed to copy text: ', err);
            return false;
        }
    }
    
    // Modern browsers
    return navigator.clipboard.writeText(text)
        .then(() => true)
        .catch(err => {
            console.error('Failed to copy text: ', err);
            return false;
        });
}

/**
 * Show a toast notification
 * @param {string} title - The toast title
 * @param {string} message - The toast message
 * @param {string} type - The toast type (success, danger, warning, info)
 * @param {number} duration - The toast duration in milliseconds
 */
function showToast(title, message, type = 'info', duration = 3000) {
    // Create toast container if it doesn't exist
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }
    
    // Create the toast
    const toastId = 'toast-' + Date.now();
    const toastHtml = `
        <div id="${toastId}" class="toast" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="toast-header bg-${type} text-white">
                <strong class="me-auto">${title}</strong>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        </div>
    `;
    
    // Add toast to container
    toastContainer.insertAdjacentHTML('beforeend', toastHtml);
    
    // Initialize and show the toast
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, {
        delay: duration
    });
    
    toast.show();
    
    // Remove toast from DOM after it's hidden
    toastElement.addEventListener('hidden.bs.toast', function() {
        toastElement.remove();
    });
}

/**
 * Parse URL parameters
 * @returns {Object} Object containing URL parameters
 */
function getUrlParams() {
    const params = {};
    const queryString = window.location.search.substring(1);
    const pairs = queryString.split('&');
    
    for (let i = 0; i < pairs.length; i++) {
        const pair = pairs[i].split('=');
        if (pair[0]) {
            params[decodeURIComponent(pair[0])] = decodeURIComponent(pair[1] || '');
        }
    }
    
    return params;
}

/**
 * Create chart for data visualization
 * @param {string} elementId - The ID of the canvas element
 * @param {Array} labels - Array of labels
 * @param {Array} data - Array of data values
 * @param {string} label - Dataset label
 * @param {string} type - Chart type (line, bar, pie, etc.)
 */
function createChart(elementId, labels, data, label, type = 'line') {
    const ctx = document.getElementById(elementId).getContext('2d');
    
    // Default colors
    const backgroundColor = 'rgba(220, 53, 69, 0.2)';
    const borderColor = 'rgba(220, 53, 69, 1)';
    
    const config = {
        type: type,
        data: {
            labels: labels,
            datasets: [{
                label: label,
                data: data,
                backgroundColor: backgroundColor,
                borderColor: borderColor,
                borderWidth: 2,
                pointBackgroundColor: borderColor,
                pointRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    };
    
    return new Chart(ctx, config);
}

/**
 * Register service worker for PWA and push notifications
 */
function registerServiceWorker() {
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/sw.js')
            .then(registration => {
                console.log('Service Worker registered with scope:', registration.scope);
                
                // Check for push notification support
                if ('PushManager' in window) {
                    console.log('Push notifications are supported');
                    
                    // Subscribe to push notifications if user is logged in
                    if (document.querySelector('meta[name="vapid-key"]')) {
                        const vapidKey = document.querySelector('meta[name="vapid-key"]').getAttribute('content');
                        if (vapidKey) {
                            subscribeToPushNotifications(registration, vapidKey);
                        }
                    }
                }
            })
            .catch(error => {
                console.error('Service Worker registration failed:', error);
            });
    }
}

/**
 * Subscribe to push notifications
 * @param {ServiceWorkerRegistration} registration - The service worker registration
 * @param {string} vapidKey - The VAPID public key
 */
function subscribeToPushNotifications(registration, vapidKey) {
    const options = {
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(vapidKey)
    };
    
    registration.pushManager.subscribe(options)
        .then(subscription => {
            // Send subscription to server
            const subscriptionJson = subscription.toJSON();
            
            fetch('/subscribe-push', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(subscriptionJson)
            })
            .then(response => response.json())
            .then(data => {
                console.log('Push subscription successful:', data);
            })
            .catch(error => {
                console.error('Error sending push subscription to server:', error);
            });
        })
        .catch(error => {
            console.error('Failed to subscribe to push notifications:', error);
        });
}

/**
 * Convert base64 string to Uint8Array for push notifications
 * @param {string} base64String - The base64 encoded string
 * @returns {Uint8Array} The converted Uint8Array
 */
function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
    const base64 = (base64String + padding)
        .replace(/\-/g, '+')
        .replace(/_/g, '/');
    
    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    
    for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
    }
    
    return outputArray;
}

// Try to register service worker when page loads
registerServiceWorker();
