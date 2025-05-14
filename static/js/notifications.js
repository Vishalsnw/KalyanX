/**
 * KalyanX - Notifications JS
 * Handles notification functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    // Load notifications on page load if user is logged in
    const notificationDropdown = document.querySelector('.notification-dropdown');
    if (notificationDropdown) {
        // Prevent dropdown from closing on click inside
        notificationDropdown.addEventListener('click', function(e) {
            e.stopPropagation();
        });

        loadNotifications();

        // Setup polling for new notifications
        setInterval(loadNotifications, 60000); // Check every minute
    }

    // Handle mark all as read button
    const markAllReadBtn = document.querySelector('.mark-all-read');
    if (markAllReadBtn) {
        markAllReadBtn.addEventListener('click', function(e) {
            e.preventDefault();
            markAllNotificationsRead();
        });
    }

    // Initialize notifications dropdown - Added based on incomplete changes
    const notifDropdown = document.getElementById('notifications-dropdown');
    if (notifDropdown) {
        notifDropdown.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
        });
    }

    // Setup push notification permission request
    setupPushNotifications();
});

/**
 * Load user notifications from server
 */
function loadNotifications() {
    fetch('/api/notifications')
        .then(response => response.json())
        .then(data => {
            updateNotificationUI(data.notifications);
            updateUnreadBadge(data.unread_count);
        })
        .catch(error => {
            console.error('Error loading notifications:', error);
        });
}

/**
 * Update notification dropdown UI
 * @param {Array} notifications - Array of notification objects
 */
function updateNotificationUI(notifications) {
    const notificationList = document.querySelector('.notification-list');
    const emptyNotifications = document.querySelector('.empty-notifications');

    if (!notificationList) return;

    // Clear existing notifications
    notificationList.innerHTML = '';

    if (notifications.length === 0) {
        emptyNotifications.classList.remove('d-none');
        return;
    }

    // Hide empty state
    emptyNotifications.classList.add('d-none');

    // Add notifications to list
    notifications.forEach(notification => {
        const notificationHtml = createNotificationHTML(notification);
        notificationList.insertAdjacentHTML('beforeend', notificationHtml);
    });

    // Add event listeners to notification items
    addNotificationEventListeners();
}

/**
 * Create HTML for a notification item
 * @param {Object} notification - Notification data
 * @returns {string} HTML for notification item
 */
function createNotificationHTML(notification) {
    const unreadClass = notification.is_read ? '' : 'unread';
    const icon = getNotificationIcon(notification.type);
    const timeAgo = formatNotificationTime(notification.created_at);

    return `
        <div class="notification-item ${unreadClass}" data-notification-id="${notification.id}">
            <div class="d-flex">
                <div class="notification-icon me-2">
                    <i class="${icon}"></i>
                </div>
                <div class="notification-content flex-grow-1">
                    <div class="notification-title">${notification.title}</div>
                    <div class="notification-message">${notification.message}</div>
                    <div class="notification-time">${timeAgo}</div>
                </div>
                <div class="notification-actions">
                    <button class="btn btn-sm text-muted mark-read-btn" data-notification-id="${notification.id}" title="Mark as read">
                        <i class="fas fa-check"></i>
                    </button>
                </div>
            </div>
        </div>
    `;
}

/**
 * Get icon class for notification type
 * @param {string} type - Notification type
 * @returns {string} FontAwesome icon class
 */
function getNotificationIcon(type) {
    switch (type) {
        case 'prediction':
            return 'fas fa-chart-line text-success';
        case 'subscription':
            return 'fas fa-crown text-warning';
        case 'referral':
            return 'fas fa-user-plus text-info';
        case 'system':
            return 'fas fa-bell text-primary';
        default:
            return 'fas fa-bell text-secondary';
    }
}

/**
 * Format notification time as relative time
 * @param {string} dateString - ISO date string
 * @returns {string} Formatted relative time
 */
function formatNotificationTime(dateString) {
    const date = new Date(dateString);

    // Get time difference in seconds
    const now = new Date();
    const diffSeconds = Math.floor((now - date) / 1000);

    if (diffSeconds < 60) {
        return 'Just now';
    } else if (diffSeconds < 3600) {
        const minutes = Math.floor(diffSeconds / 60);
        return `${minutes} ${minutes === 1 ? 'minute' : 'minutes'} ago`;
    } else if (diffSeconds < 86400) {
        const hours = Math.floor(diffSeconds / 3600);
        return `${hours} ${hours === 1 ? 'hour' : 'hours'} ago`;
    } else if (diffSeconds < 604800) {
        const days = Math.floor(diffSeconds / 86400);
        return `${days} ${days === 1 ? 'day' : 'days'} ago`;
    } else {
        // Format as date for older notifications
        return date.toLocaleDateString();
    }
}

/**
 * Update unread notification badge
 * @param {number} count - Unread notification count
 */
function updateUnreadBadge(count) {
    const badge = document.querySelector('.notification-badge');
    if (!badge) return;

    if (count > 0) {
        badge.textContent = count;
        badge.classList.remove('d-none');
    } else {
        badge.textContent = '0';
        badge.classList.add('d-none');
    }
}

/**
 * Add event listeners to notification items
 */
function addNotificationEventListeners() {
    // Mark as read buttons
    const markReadButtons = document.querySelectorAll('.mark-read-btn');
    markReadButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.stopPropagation();
            const notificationId = this.getAttribute('data-notification-id');
            markNotificationRead(notificationId);
        });
    });

    // Notification item click
    const notificationItems = document.querySelectorAll('.notification-item');
    notificationItems.forEach(item => {
        item.addEventListener('click', function() {
            const notificationId = this.getAttribute('data-notification-id');
            if (!this.classList.contains('unread')) return;

            markNotificationRead(notificationId);
        });
    });
}

/**
 * Mark a notification as read
 * @param {number} notificationId - ID of the notification
 */
function markNotificationRead(notificationId) {
    fetch(`/api/notifications/${notificationId}/read`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update UI
            const notification = document.querySelector(`.notification-item[data-notification-id="${notificationId}"]`);
            if (notification) {
                notification.classList.remove('unread');
            }

            // Update unread count
            updateUnreadBadge(data.unread_count);
        }
    })
    .catch(error => {
        console.error('Error marking notification as read:', error);
    });
}

/**
 * Mark all notifications as read
 */
function markAllNotificationsRead() {
    fetch('/api/notifications/read-all', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update UI
            const notifications = document.querySelectorAll('.notification-item.unread');
            notifications.forEach(notification => {
                notification.classList.remove('unread');
            });

            // Update unread count
            updateUnreadBadge(0);
        }
    })
    .catch(error => {
        console.error('Error marking all notifications as read:', error);
    });
}

/**
 * Setup push notification permission
 */
function setupPushNotifications() {
    // Check if push notifications are supported
    if (!('Notification' in window)) {
        console.log('This browser does not support notifications');
        return;
    }

    // Check if service worker is supported
    if (!('serviceWorker' in navigator)) {
        console.log('Service Worker not supported');
        return;
    }

    // Initialize Firebase first
    if (typeof firebase === 'undefined') {
        console.error('Firebase not initialized');
        return;
    }

    const messaging = firebase.messaging?.();
    if (!messaging) {
        console.log('Firebase messaging not available');
        return;
    }

    // Register service worker with error handling
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/static/js/firebase-messaging-sw.js')
            .then(function(registration) {
                console.log('Service Worker registered successfully');
            })
            .catch(function(err) {
                console.log('Service Worker registration failed', err);
            });
    }

    // Request permission if not granted
    if (Notification.permission !== 'granted' && Notification.permission !== 'denied') {
        // Add notification permission button if it exists
        const notificationPermissionBtn = document.getElementById('enable-notifications');
        if (notificationPermissionBtn) {
            notificationPermissionBtn.classList.remove('d-none');

            notificationPermissionBtn.addEventListener('click', function() {
                requestNotificationPermission();
            });
        }
    }
}

/**
 * Request notification permission
 */
function requestNotificationPermission() {
    Notification.requestPermission()
        .then(permission => {
            if (permission === 'granted') {
                showToast('Success', 'Push notifications enabled!', 'success');

                // Hide permission button
                const notificationPermissionBtn = document.getElementById('enable-notifications');
                if (notificationPermissionBtn) {
                    notificationPermissionBtn.classList.add('d-none');
                }

                // Register service worker for push if not already registered
                if ('serviceWorker' in navigator) {
                    navigator.serviceWorker.ready
                        .then(registration => {
                            // Get VAPID key from meta tag
                            const vapidKey = document.querySelector('meta[name="vapid-key"]')?.getAttribute('content');
                            if (vapidKey) {
                                subscribeToPushNotifications(registration, vapidKey);
                            }
                        });
                }
            } else {
                showToast('Notice', 'Push notification permission denied', 'warning');
            }
        });
}