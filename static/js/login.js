/**
 * KalyanX - Login JS
 * Handles the login functionality with Firebase and mobile registration
 */

// Global Firebase auth state
let firebaseInitialized = false;
let firebaseAuthReady = false;

// Initialize Firebase only once when needed
function initFirebaseAuth() {
    if (firebaseInitialized) {
        return Promise.resolve();
    }
    
    console.log("Initializing Firebase auth");
    firebaseInitialized = true;
    
    // Firebase is already initialized in base template, just need to check if auth is ready
    return new Promise((resolve) => {
        if (typeof firebase !== 'undefined' && firebase.auth) {
            firebaseAuthReady = true;
            resolve();
        } else {
            // Check every 100ms if Firebase auth is ready
            const checkInterval = setInterval(() => {
                if (typeof firebase !== 'undefined' && firebase.auth) {
                    clearInterval(checkInterval);
                    firebaseAuthReady = true;
                    resolve();
                }
            }, 100);
            
            // Timeout after 5 seconds
            setTimeout(() => {
                clearInterval(checkInterval);
                console.error("Firebase auth initialization timed out");
                resolve(); // Resolve anyway to prevent hanging
            }, 5000);
        }
    });
}

// Validate mobile number format
function validateMobile(mobile) {
    return /^[0-9]{10}$/.test(mobile);
}

// Show or hide a form status message
function showFormStatus(message, type = 'danger') {
    const statusDiv = document.getElementById('form-status');
    if (!statusDiv) return;
    
    statusDiv.textContent = message;
    statusDiv.className = `alert alert-${type} mt-3`;
    statusDiv.style.display = 'block';
}

// Check if this is an admin login
function isAdminLogin() {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get('admin') === '1';
}

// Handle Google Sign-In
function signInWithGoogle() {
    const loadingIndicator = document.getElementById('loading-indicator');
    if (loadingIndicator) loadingIndicator.classList.remove('d-none');
    
    // If this is an admin login, show warning
    if (isAdminLogin()) {
        if (confirm('Admin login requires special privileges. Are you sure you want to continue with Google sign-in?')) {
            return proceedWithGoogleSignIn();
        } else {
            if (loadingIndicator) loadingIndicator.classList.add('d-none');
            return Promise.reject(new Error('Admin login cancelled'));
        }
    } else {
        return proceedWithGoogleSignIn();
    }
}

// Proceed with Google Sign-In
function proceedWithGoogleSignIn() {
    return initFirebaseAuth()
        .then(() => {
            const provider = new firebase.auth.GoogleAuthProvider();
            return firebase.auth().signInWithRedirect(provider);
        })
        .catch((error) => {
            console.error('Google sign-in error:', error);
            const loadingIndicator = document.getElementById('loading-indicator');
            if (loadingIndicator) loadingIndicator.classList.add('d-none');
            showFormStatus(error.message || 'Google sign-in failed. Please try again.');
        });
}

document.addEventListener('DOMContentLoaded', function() {
    // Set up Google Sign-In button
    const googleSignInBtn = document.getElementById('google-sign-in-btn');
    if (googleSignInBtn) {
        googleSignInBtn.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Add loading indicator
            googleSignInBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Signing in...';
            googleSignInBtn.disabled = true;
            
            signInWithGoogle()
                .catch(error => {
                    console.error('Sign-in error:', error);
                    googleSignInBtn.innerHTML = '<img src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg" alt="Google" width="24" height="24" class="me-2"><strong>Sign in with Google</strong>';
                    googleSignInBtn.disabled = false;
                });
        });
    }
    
    // Set up mobile registration form validation
    const mobileRegistrationForm = document.getElementById('mobile-registration-form');
    if (mobileRegistrationForm) {
        const mobileInput = document.getElementById('mobile');
        
        mobileInput.addEventListener('input', function() {
            // Remove non-numeric characters
            this.value = this.value.replace(/\D/g, '');
            
            // Limit to 10 digits
            if (this.value.length > 10) {
                this.value = this.value.slice(0, 10);
            }
        });
        
        mobileRegistrationForm.addEventListener('submit', function(e) {
            const mobile = mobileInput.value.trim();
            
            if (!validateMobile(mobile)) {
                e.preventDefault();
                showFormStatus('Please enter a valid 10-digit mobile number');
            }
        });
    }
    
    // Check if we need to handle Firebase auth result (after redirect)
    firebase.auth().getRedirectResult()
        .then((result) => {
            if (result.user) {
                // User signed in with redirect
                return result.user.getIdToken()
                    .then(idToken => {
                        // Send token to backend
                        return fetch('/api/verify-firebase-token', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({
                                idToken: idToken,
                                pin: '1234'  // Default PIN
                            })
                        });
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            window.location.href = data.redirect || '/dashboard';
                        } else {
                            throw new Error(data.message || 'Authentication failed');
                        }
                    });
            }
        })
        .catch((error) => {
            console.error('Redirect result error:', error);
            // Only show error message if it's not just the absence of a redirect result
            if (error.code !== 'auth/credential-already-in-use') {
                showFormStatus(error.message || 'Authentication failed. Please try again.');
            }
        });
});