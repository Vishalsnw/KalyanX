/**
 * KalyanX - Subscription JS
 * Handles subscription-related functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    // Subscribe button click handler
    const subscribeButtons = document.querySelectorAll('.subscribe-btn');
    subscribeButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Redirect to checkout
            window.location.href = this.getAttribute('href');
        });
    });
    
    // Initialize Razorpay if on checkout page
    const razorpayContainer = document.getElementById('razorpay-container');
    if (razorpayContainer) {
        const orderId = razorpayContainer.getAttribute('data-order-id');
        const amount = razorpayContainer.getAttribute('data-amount');
        const currency = razorpayContainer.getAttribute('data-currency');
        const keyId = razorpayContainer.getAttribute('data-key');
        
        initializeRazorpay(orderId, amount, currency, keyId);
    }
    
    // Subscription history page - format dates
    const subscriptionDates = document.querySelectorAll('.format-date');
    subscriptionDates.forEach(element => {
        const dateString = element.textContent;
        if (dateString) {
            const date = new Date(dateString);
            element.textContent = formatDate(date);
        }
    });
    
    // Referral link copy button
    const copyReferralBtn = document.getElementById('copy-referral-link');
    if (copyReferralBtn) {
        copyReferralBtn.addEventListener('click', function() {
            const referralLink = document.getElementById('referral-link').textContent;
            copyToClipboard(referralLink)
                .then(() => {
                    const originalText = this.innerHTML;
                    this.innerHTML = '<i class="fas fa-check"></i> Copied!';
                    setTimeout(() => {
                        this.innerHTML = originalText;
                    }, 2000);
                })
                .catch(() => {
                    showToast('Error', 'Failed to copy referral link', 'danger');
                });
        });
    }
    
    // Days remaining progress bar
    const daysRemainingElement = document.getElementById('days-remaining');
    if (daysRemainingElement) {
        const daysRemaining = parseInt(daysRemainingElement.getAttribute('data-days') || '0');
        const totalDays = parseInt(daysRemainingElement.getAttribute('data-total-days') || '30');
        
        const progressBar = document.getElementById('subscription-progress');
        if (progressBar) {
            const percentage = Math.min(100, Math.max(0, (daysRemaining / totalDays) * 100));
            progressBar.style.width = `${percentage}%`;
            
            // Set color based on days remaining
            if (daysRemaining <= 3) {
                progressBar.classList.add('bg-danger');
            } else if (daysRemaining <= 7) {
                progressBar.classList.add('bg-warning');
            } else {
                progressBar.classList.add('bg-success');
            }
        }
    }
});

/**
 * Initialize Razorpay payment gateway
 * @param {string} orderId - Razorpay order ID
 * @param {string} amount - Payment amount
 * @param {string} currency - Payment currency
 * @param {string} keyId - Razorpay key ID
 */
function initializeRazorpay(orderId, amount, currency, keyId) {
    const options = {
        key: keyId,
        amount: parseFloat(amount) * 100, // Convert to paise
        currency: currency,
        name: 'KalyanX',
        description: 'Premium Subscription',
        image: '/static/img/logo.svg',
        order_id: orderId,
        handler: function(response) {
            // Create hidden form to submit payment data
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = '/payment/verify';
            
            // Add CSRF token if available
            const csrfToken = document.querySelector('meta[name="csrf-token"]');
            if (csrfToken) {
                const csrfInput = document.createElement('input');
                csrfInput.type = 'hidden';
                csrfInput.name = 'csrf_token';
                csrfInput.value = csrfToken.getAttribute('content');
                form.appendChild(csrfInput);
            }
            
            // Add payment details
            for (const key in response) {
                const input = document.createElement('input');
                input.type = 'hidden';
                input.name = key;
                input.value = response[key];
                form.appendChild(input);
            }
            
            // Submit form
            document.body.appendChild(form);
            form.submit();
        },
        prefill: {
            name: '',
            email: '',
            contact: ''
        },
        notes: {
            address: ''
        },
        theme: {
            color: '#dc3545'
        }
    };
    
    const rzp = new Razorpay(options);
    
    // Open Razorpay automatically
    rzp.open();
    
    // Pay button click handler
    const payButton = document.getElementById('pay-button');
    if (payButton) {
        payButton.addEventListener('click', function() {
            rzp.open();
        });
    }
}

/**
 * Get subscription status
 * Updates the UI with the latest subscription information
 */
function getSubscriptionStatus() {
    fetch('/api/subscription-status')
        .then(response => response.json())
        .then(data => {
            // Update subscription badge in navbar
            const subscriptionBadge = document.querySelector('.subscription-badge');
            if (subscriptionBadge) {
                if (data.is_premium) {
                    subscriptionBadge.textContent = 'Premium';
                    subscriptionBadge.classList.remove('bg-info');
                    subscriptionBadge.classList.add('bg-warning');
                } else if (data.is_trial_active) {
                    subscriptionBadge.textContent = 'Trial';
                    subscriptionBadge.classList.remove('bg-warning');
                    subscriptionBadge.classList.add('bg-info');
                } else {
                    subscriptionBadge.textContent = 'Free';
                    subscriptionBadge.classList.remove('bg-warning', 'bg-info');
                    subscriptionBadge.classList.add('bg-secondary');
                }
            }
            
            // Update subscription info on subscription page
            const subscriptionStatusElement = document.getElementById('subscription-status');
            if (subscriptionStatusElement) {
                if (data.is_premium) {
                    subscriptionStatusElement.textContent = `Premium (${data.days_remaining} days remaining)`;
                    subscriptionStatusElement.classList.add('text-warning');
                } else if (data.is_trial_active) {
                    subscriptionStatusElement.textContent = `Trial (${data.days_remaining} days remaining)`;
                    subscriptionStatusElement.classList.add('text-info');
                } else {
                    subscriptionStatusElement.textContent = 'Expired';
                    subscriptionStatusElement.classList.add('text-danger');
                }
            }
            
            // Update days remaining progress bar
            const daysRemainingElement = document.getElementById('days-remaining');
            if (daysRemainingElement) {
                daysRemainingElement.textContent = data.days_remaining;
                daysRemainingElement.setAttribute('data-days', data.days_remaining);
                
                const progressBar = document.getElementById('subscription-progress');
                if (progressBar) {
                    const totalDays = data.is_premium ? 30 : 7; // 30 days for premium, 7 for trial
                    const percentage = Math.min(100, Math.max(0, (data.days_remaining / totalDays) * 100));
                    progressBar.style.width = `${percentage}%`;
                    
                    // Set color based on days remaining
                    progressBar.className = 'progress-bar';
                    if (data.days_remaining <= 3) {
                        progressBar.classList.add('bg-danger');
                    } else if (data.days_remaining <= 7) {
                        progressBar.classList.add('bg-warning');
                    } else {
                        progressBar.classList.add('bg-success');
                    }
                }
            }
            
            // Update expiry date display
            const expiryDateElement = document.getElementById('expiry-date');
            if (expiryDateElement) {
                const expiryDate = data.is_premium ? data.premium_end_date : data.trial_end_date;
                if (expiryDate) {
                    expiryDateElement.textContent = expiryDate;
                }
            }
        })
        .catch(error => {
            console.error('Error fetching subscription status:', error);
        });
}

// If user is on subscription page, get status on load
if (document.getElementById('subscription-status')) {
    getSubscriptionStatus();
}
