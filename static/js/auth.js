/**
 * KalyanX - Authentication JS
 * Handles user authentication functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    // Mobile number validation
    const mobileInput = document.getElementById('mobile');
    if (mobileInput) {
        mobileInput.addEventListener('input', function() {
            validateMobile(this);
        });
    }
    
    // PIN validation
    const pinInput = document.getElementById('pin');
    if (pinInput) {
        pinInput.addEventListener('input', function() {
            validatePin(this);
        });
    }
    
    // Confirm PIN validation
    const confirmPinInput = document.getElementById('confirm_pin');
    if (confirmPinInput) {
        confirmPinInput.addEventListener('input', function() {
            validateConfirmPin(this, pinInput);
        });
    }
    
    // Login form submission
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            if (!validateLoginForm()) {
                e.preventDefault();
            }
        });
    }
    
    // Register form submission
    const registerForm = document.getElementById('register-form');
    if (registerForm) {
        registerForm.addEventListener('submit', function(e) {
            // Check if using Firebase auth
            const activeTab = document.querySelector('#registerTabs .nav-link.active');
            if (activeTab && activeTab.id === 'email-tab') {
                const useFirebaseEmail = document.getElementById('use-firebase-email');
                if (useFirebaseEmail && useFirebaseEmail.checked) {
                    // Using Firebase email auth, prevent normal submission
                    e.preventDefault();
                    return;
                }
            } else if (activeTab && activeTab.id === 'mobile-tab') {
                const useFirebaseMobile = document.getElementById('use-firebase-mobile');
                if (useFirebaseMobile && useFirebaseMobile.checked) {
                    // Using Firebase phone auth, prevent normal submission
                    e.preventDefault();
                    return;
                }
            }
            
            // Using regular auth, validate form
            if (!validateRegisterForm()) {
                e.preventDefault();
            }
        });
    }
    
    // Set up Firebase auth toggle for email
    const useFirebaseEmail = document.getElementById('use-firebase-email');
    if (useFirebaseEmail) {
        useFirebaseEmail.addEventListener('change', function() {
            const regularEmailReg = document.getElementById('regular-email-registration');
            const firebaseEmailReg = document.getElementById('firebase-email-registration');
            const mainRegisterBtn = document.getElementById('main-register-btn');
            
            if (this.checked) {
                // Show Firebase, hide regular
                regularEmailReg.classList.add('d-none');
                firebaseEmailReg.classList.remove('d-none');
                if (mainRegisterBtn) mainRegisterBtn.classList.add('d-none');
            } else {
                // Show regular, hide Firebase
                regularEmailReg.classList.remove('d-none');
                firebaseEmailReg.classList.add('d-none');
                if (mainRegisterBtn) mainRegisterBtn.classList.remove('d-none');
            }
        });
        
        // Trigger initial state
        useFirebaseEmail.dispatchEvent(new Event('change'));
    }
    
    // Set up Firebase auth toggle for mobile
    const useFirebaseMobile = document.getElementById('use-firebase-mobile');
    if (useFirebaseMobile) {
        useFirebaseMobile.addEventListener('change', function() {
            const regularMobileReg = document.getElementById('regular-mobile-registration');
            const firebaseMobileReg = document.getElementById('firebase-mobile-registration');
            const mainRegisterBtn = document.getElementById('main-register-btn');
            
            if (this.checked) {
                // Show Firebase, hide regular
                regularMobileReg.classList.add('d-none');
                firebaseMobileReg.classList.remove('d-none');
                if (mainRegisterBtn) mainRegisterBtn.classList.add('d-none');
            } else {
                // Show regular, hide Firebase
                regularMobileReg.classList.remove('d-none');
                firebaseMobileReg.classList.add('d-none');
                if (mainRegisterBtn) mainRegisterBtn.classList.remove('d-none');
            }
        });
        
        // Trigger initial state
        useFirebaseMobile.dispatchEvent(new Event('change'));
    }
    
    // Main register button override (in case the form has duplicate buttons)
    const mainRegisterBtn = document.getElementById('main-register-btn');
    if (mainRegisterBtn && registerForm) {
        mainRegisterBtn.addEventListener('click', function(e) {
            e.preventDefault();
            if (validateRegisterForm()) {
                registerForm.submit();
            }
        });
    }
    
    // OTP form setup
    setupOtpForm();
    
    // Referral code copy
    const copyReferralBtn = document.getElementById('copy-referral');
    if (copyReferralBtn) {
        copyReferralBtn.addEventListener('click', function() {
            const referralCode = document.getElementById('referral-code').textContent;
            copyToClipboard(referralCode)
                .then(() => {
                    showToast('Success', 'Referral code copied to clipboard!', 'success');
                })
                .catch(() => {
                    showToast('Error', 'Failed to copy referral code', 'danger');
                });
        });
    }
    
    // Resend OTP
    const resendOtpBtn = document.getElementById('resend-otp');
    if (resendOtpBtn) {
        resendOtpBtn.addEventListener('click', function(e) {
            e.preventDefault();
            resendOtp();
        });
    }
    
    // Check if there's a referral code in the URL
    const urlParams = new URLSearchParams(window.location.search);
    const referralCode = urlParams.get('ref');
    if (referralCode) {
        const referralInput = document.getElementById('referral_code');
        if (referralInput) {
            referralInput.value = referralCode;
            document.getElementById('referral-section').classList.remove('d-none');
        }
    }
    
    // Toggle referral code section
    const haveReferralLink = document.getElementById('have-referral-link');
    if (haveReferralLink) {
        haveReferralLink.addEventListener('click', function(e) {
            e.preventDefault();
            document.getElementById('referral-section').classList.toggle('d-none');
        });
    }
});

/**
 * Validate mobile number format
 * @param {HTMLInputElement} input - The mobile input element
 * @returns {boolean} Whether the mobile is valid
 */
function validateMobile(input) {
    const value = input.value.trim();
    // Accept any mobile number with 10-15 digits
    const mobileRegex = /^\d{10,15}$/;
    
    const isValid = mobileRegex.test(value);
    updateValidationUI(input, isValid, 'Please enter a valid mobile number (10-15 digits)');
    
    if (isValid && document.getElementById('check-mobile-btn')) {
        checkMobileExists(value);
    }
    
    return isValid;
}

/**
 * Validate PIN format
 * @param {HTMLInputElement} input - The PIN input element
 * @returns {boolean} Whether the PIN is valid
 */
function validatePin(input) {
    const value = input.value.trim();
    const pinRegex = /^\d{4}$/; // 4-digit PIN
    
    const isValid = pinRegex.test(value);
    updateValidationUI(input, isValid, 'PIN must be 4 digits');
    
    return isValid;
}

/**
 * Validate confirm PIN matches original PIN
 * @param {HTMLInputElement} confirmInput - The confirm PIN input element
 * @param {HTMLInputElement} pinInput - The original PIN input element
 * @returns {boolean} Whether the PINs match
 */
function validateConfirmPin(confirmInput, pinInput) {
    const confirmValue = confirmInput.value.trim();
    const pinValue = pinInput.value.trim();
    
    const isValid = confirmValue === pinValue;
    updateValidationUI(confirmInput, isValid, 'PINs do not match');
    
    return isValid;
}

/**
 * Update input validation UI
 * @param {HTMLInputElement} input - The input element
 * @param {boolean} isValid - Whether the input is valid
 * @param {string} errorMessage - The error message to display
 */
function updateValidationUI(input, isValid, errorMessage) {
    const feedbackElement = input.nextElementSibling;
    
    if (isValid) {
        input.classList.remove('is-invalid');
        input.classList.add('is-valid');
        if (feedbackElement && feedbackElement.classList.contains('invalid-feedback')) {
            feedbackElement.textContent = '';
        }
    } else {
        input.classList.remove('is-valid');
        input.classList.add('is-invalid');
        if (feedbackElement && feedbackElement.classList.contains('invalid-feedback')) {
            feedbackElement.textContent = errorMessage;
        }
    }
}

/**
 * Validate identifier (email or mobile)
 * @param {HTMLInputElement} identifierInput - The identifier input field
 * @returns {boolean} Whether the identifier is valid
 */
function validateIdentifier(identifierInput) {
    const identifier = identifierInput.value.trim();
    const feedbackElement = identifierInput.nextElementSibling;
    
    if (!identifier) {
        updateValidationUI(identifierInput, false, 'Email or mobile number is required');
        return false;
    }
    
    // Check if identifier is an email or mobile number
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    const mobileRegex = /^[6-9]\d{9}$/;
    
    if (!emailRegex.test(identifier) && !mobileRegex.test(identifier)) {
        updateValidationUI(identifierInput, false, 'Please enter a valid email or mobile number');
        return false;
    }
    
    updateValidationUI(identifierInput, true, '');
    return true;
}

/**
 * Validate login form
 * @returns {boolean} Whether the form is valid
 */
function validateLoginForm() {
    const identifierInput = document.getElementById('identifier');
    const pinInput = document.getElementById('pin');
    
    // Validate identifier
    const isIdentifierValid = validateIdentifier(identifierInput);
    
    // Validate PIN
    const isPinValid = validatePin(pinInput);
    
    return isIdentifierValid && isPinValid;
}

/**
 * Validate an email address
 * @param {HTMLInputElement} emailInput - The email input field
 * @returns {boolean} Whether the email is valid
 */
function validateEmail(emailInput) {
    // Email validation regex
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    const email = emailInput.value.trim();
    const feedbackElement = emailInput.nextElementSibling;
    
    if (!email) {
        emailInput.classList.remove('is-valid');
        emailInput.classList.add('is-invalid');
        if (feedbackElement && feedbackElement.classList.contains('invalid-feedback')) {
            feedbackElement.textContent = 'Email address is required';
        }
        return false;
    }
    
    if (!emailRegex.test(email)) {
        emailInput.classList.remove('is-valid');
        emailInput.classList.add('is-invalid');
        if (feedbackElement && feedbackElement.classList.contains('invalid-feedback')) {
            feedbackElement.textContent = 'Please enter a valid email address';
        }
        return false;
    }
    
    // Check if email already exists
    checkEmailExists(email);
    
    emailInput.classList.remove('is-invalid');
    emailInput.classList.add('is-valid');
    return true;
}

/**
 * Validate registration form
 * @returns {boolean} Whether the form is valid
 */
function validateRegisterForm() {
    // Get active tab
    const activeTab = document.querySelector('#registerTabs .nav-link.active');
    
    if (!activeTab) return false;
    
    // Check active tab (email or mobile)
    if (activeTab.id === 'email-tab') {
        const emailInput = document.getElementById('email');
        return validateEmail(emailInput);
    } else if (activeTab.id === 'mobile-tab') {
        const mobileInput = document.getElementById('mobile');
        return validateMobile(mobileInput);
    }
    
    return false;
}

/**
 * Check if mobile number already exists
 * @param {string} mobile - The mobile number to check
 */
function checkMobileExists(mobile) {
    const formData = new FormData();
    formData.append('mobile', mobile);
    
    fetch('/check-mobile', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        const mobileInput = document.getElementById('mobile');
        const feedbackElement = mobileInput.nextElementSibling;
        
        if (data.exists) {
            mobileInput.classList.remove('is-valid');
            mobileInput.classList.add('is-invalid');
            if (feedbackElement && feedbackElement.classList.contains('invalid-feedback')) {
                feedbackElement.textContent = data.message;
            }
        }
    })
    .catch(error => {
        console.error('Error checking mobile:', error);
    });
}

/**
 * Check if email already exists
 * @param {string} email - The email to check
 */
function checkEmailExists(email) {
    const formData = new FormData();
    formData.append('email', email);
    
    fetch('/check-email', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        const emailInput = document.getElementById('email');
        const feedbackElement = emailInput.nextElementSibling;
        
        if (data.exists) {
            emailInput.classList.remove('is-valid');
            emailInput.classList.add('is-invalid');
            if (feedbackElement && feedbackElement.classList.contains('invalid-feedback')) {
                feedbackElement.textContent = data.message;
            }
        }
    })
    .catch(error => {
        console.error('Error checking email:', error);
    });
}

/**
 * Set up OTP input form for auto-tabbing between digits
 */
function setupOtpForm() {
    const otpInputs = document.querySelectorAll('.otp-input');
    if (otpInputs.length === 0) return;
    
    // Focus on first input
    otpInputs[0].focus();
    
    // Setup each input
    otpInputs.forEach((input, index) => {
        // Auto-tab when digit is entered
        input.addEventListener('input', function() {
            if (this.value.length === 1) {
                if (index < otpInputs.length - 1) {
                    otpInputs[index + 1].focus();
                }
            }
        });
        
        // Handle backspace
        input.addEventListener('keydown', function(e) {
            if (e.key === 'Backspace' && this.value.length === 0 && index > 0) {
                otpInputs[index - 1].focus();
            }
        });
        
        // Handle paste
        input.addEventListener('paste', function(e) {
            e.preventDefault();
            const pasteData = e.clipboardData.getData('text');
            if (/^\d+$/.test(pasteData)) {
                fillOtpFromPaste(pasteData, otpInputs, index);
            }
        });
    });
    
    // Handle form submission
    const otpForm = document.getElementById('otp-form');
    if (otpForm) {
        otpForm.addEventListener('submit', function(e) {
            // Combine OTP inputs into hidden field
            const combinedOtp = Array.from(otpInputs).map(input => input.value).join('');
            const otpHiddenInput = document.getElementById('otp');
            if (otpHiddenInput) {
                otpHiddenInput.value = combinedOtp;
            }
            
            // Validate OTP
            if (combinedOtp.length !== otpInputs.length || !/^\d+$/.test(combinedOtp)) {
                e.preventDefault();
                showToast('Error', 'Please enter a valid OTP', 'danger');
            }
        });
    }
}

/**
 * Fill OTP inputs from pasted value
 * @param {string} pasteData - The pasted data
 * @param {NodeList} inputs - The OTP input elements
 * @param {number} startIndex - The index to start filling from
 */
function fillOtpFromPaste(pasteData, inputs, startIndex) {
    // Only consider digits
    const digits = pasteData.replace(/\D/g, '');
    
    // Fill inputs
    for (let i = 0; i < inputs.length - startIndex && i < digits.length; i++) {
        inputs[startIndex + i].value = digits[i];
    }
    
    // Focus on the appropriate input
    const focusIndex = Math.min(startIndex + digits.length, inputs.length - 1);
    inputs[focusIndex].focus();
}

/**
 * Resend OTP
 */
function resendOtp() {
    const resendBtn = document.getElementById('resend-otp');
    
    // Disable button to prevent spam
    resendBtn.disabled = true;
    resendBtn.textContent = 'Sending...';
    
    // Determine if we're on email verification page
    const isEmailVerification = window.location.href.includes('verify-email-otp');
    const endpoint = isEmailVerification ? '/resend-email-otp' : '/resend-otp';
    
    fetch(endpoint, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('Success', 'OTP sent successfully', 'success');
            
            // Start countdown
            let countdown = 60;
            resendBtn.textContent = `Resend OTP (${countdown}s)`;
            
            const timer = setInterval(() => {
                countdown--;
                resendBtn.textContent = `Resend OTP (${countdown}s)`;
                
                if (countdown <= 0) {
                    clearInterval(timer);
                    resendBtn.disabled = false;
                    resendBtn.textContent = 'Resend OTP';
                }
            }, 1000);
        } else {
            showToast('Error', data.message || 'Failed to resend OTP', 'danger');
            resendBtn.disabled = false;
            resendBtn.textContent = 'Resend OTP';
        }
    })
    .catch(error => {
        console.error('Error resending OTP:', error);
        showToast('Error', 'Failed to resend OTP', 'danger');
        resendBtn.disabled = false;
        resendBtn.textContent = 'Resend OTP';
    });
}
