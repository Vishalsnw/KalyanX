/**
 * KalyanX - Firebase Integration
 * Handles Firebase authentication and integration
 */

// Firebase app is initialized in the base template 
// This file provides helper functions for Firebase authentication

// Helper function to send email verification
function sendEmailVerification(email, actionCodeSettings) {
  return firebase.auth().sendSignInLinkToEmail(email, actionCodeSettings)
    .then(() => {
      // Email link sent successfully
      console.log('Email verification link sent successfully');
      window.localStorage.setItem('emailForSignIn', email);
      return true;
    })
    .catch((error) => {
      // Error occurred
      console.error('Error sending email verification link:', error);
      return false;
    });
}

// Configure FirebaseUI for authentication
function setupFirebaseUI(containerId) {
  // Get the FirebaseUI instance
  const ui = new firebaseui.auth.AuthUI(firebase.auth());
  
  // Configure FirebaseUI
  const uiConfig = {
    // Redirect after successful authentication
    callbacks: {
      signInSuccessWithAuthResult: function(authResult, redirectUrl) {
        // Process the authentication result
        processFirebaseAuth(authResult.user);
        return false; // Don't redirect, we'll handle it manually
      },
      uiShown: function() {
        // UI is rendered, hide the loader if it exists
        const loader = document.getElementById('firebase-loader');
        if (loader) {
          loader.style.display = 'none';
        }
      }
    },
    // Options for sign-in flows
    signInFlow: 'redirect', // 'popup' or 'redirect'
    signInSuccessUrl: '/dashboard', // Redirect after successful sign-in
    signInOptions: [
      // List of OAuth providers supported
      firebase.auth.GoogleAuthProvider.PROVIDER_ID,
      firebase.auth.EmailAuthProvider.PROVIDER_ID,
      {
        provider: firebase.auth.PhoneAuthProvider.PROVIDER_ID,
        recaptchaParameters: {
          type: 'image',
          size: 'normal',
          badge: 'bottomleft'
        },
        defaultCountry: 'IN', // Set default country to India
        whitelistedCountries: ['IN'] // Only allow Indian phone numbers
      }
    ],
    // Terms of service URL
    tosUrl: '/terms',
    // Privacy policy URL
    privacyPolicyUrl: '/privacy-policy'
  };
  
  // Start the FirebaseUI Auth
  ui.start('#' + containerId, uiConfig);
}

// Send phone OTP (for direct integration without FirebaseUI)
async function sendPhoneOTP(phoneNumber, recaptchaContainerId) {
  try {
    // Create a reCAPTCHA verifier
    const recaptchaVerifier = new firebase.auth.RecaptchaVerifier(recaptchaContainerId, {
      'size': 'normal',
      'callback': (response) => {
        // reCAPTCHA solved, allow signInWithPhoneNumber
        console.log('reCAPTCHA verified');
      },
      'expired-callback': () => {
        // Response expired. Ask user to solve reCAPTCHA again
        console.log('reCAPTCHA expired');
      }
    });
    
    // Render the reCAPTCHA
    recaptchaVerifier.render();
    
    // Send OTP
    const confirmationResult = await firebase.auth().signInWithPhoneNumber(phoneNumber, recaptchaVerifier);
    
    // Store confirmation result for later verification
    window.confirmationResult = confirmationResult;
    
    return true;
  } catch (error) {
    console.error('Error sending OTP:', error);
    return false;
  }
}

// Verify phone OTP (for direct integration without FirebaseUI)
async function verifyPhoneOTP(code) {
  try {
    if (!window.confirmationResult) {
      console.error('No confirmation result found. Please send OTP first.');
      return false;
    }
    
    const result = await window.confirmationResult.confirm(code);
    // User signed in successfully
    const user = result.user;
    processFirebaseAuth(user);
    return true;
  } catch (error) {
    console.error('Error verifying OTP:', error);
    return false;
  }
}

// Process Firebase authentication
async function processFirebaseAuth(user) {
  try {
    if (!user) {
      console.error('No user provided');
      return false;
    }
    
    // Get ID token
    const idToken = await user.getIdToken();
    
    // Send token to backend for verification and account creation/login
    const pinInput = document.getElementById('pin');
    const pin = pinInput ? pinInput.value : '1234'; // Default PIN if not provided
    
    // Get referral code if any
    const urlParams = new URLSearchParams(window.location.search);
    const referralCode = urlParams.get('ref');
    
    // Prepare data for backend
    const data = {
      idToken: idToken,
      pin: pin
    };
    
    // Add referral code if present
    if (referralCode) {
      data.referralCode = referralCode;
    }
    
    // Send to backend
    const response = await fetch('/api/verify-firebase-token', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data)
    });
    
    const result = await response.json();
    
    if (result.success) {
      // If successful, redirect to specified URL
      window.location.href = result.redirect || '/dashboard';
      return true;
    } else {
      // Show error message
      alert(result.message || 'Authentication failed. Please try again.');
      return false;
    }
  } catch (error) {
    console.error('Error processing Firebase auth:', error);
    alert('Authentication failed. Please try again.');
    return false;
  }
}

// Set up auth state listeners
function setupAuthListeners() {
  firebase.auth().onAuthStateChanged((user) => {
    if (user) {
      // User is signed in
      console.log('User is signed in:', user.uid);
    } else {
      // User is signed out
      console.log('User is signed out');
    }
  });
}

// Sign out from Firebase
async function firebaseSignOut() {
  try {
    await firebase.auth().signOut();
    return true;
  } catch (error) {
    console.error('Error signing out:', error);
    return false;
  }
}

// Add event listeners and initialize Firebase functions when the page loads
document.addEventListener('DOMContentLoaded', function() {
  // Add any global event listeners here
  const firebaseAuthForm = document.getElementById('firebase-auth-form');
  if (firebaseAuthForm) {
    firebaseAuthForm.addEventListener('submit', function(e) {
      e.preventDefault();
      // Process the form submission
      completeRegistration();
    });
  }
});

// Complete registration after Firebase authentication
async function completeRegistration() {
  const user = firebase.auth().currentUser;
  if (!user) {
    alert('Please authenticate with Firebase first');
    return;
  }
  
  // Get PIN from form
  const pinInput = document.getElementById('pin');
  if (!pinInput || !pinInput.value) {
    alert('Please enter a 4-digit PIN');
    return;
  }
  
  // Process authentication
  await processFirebaseAuth(user);
}