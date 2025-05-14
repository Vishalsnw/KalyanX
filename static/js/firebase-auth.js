// Firebase Authentication Module

// Initialize Firebase if not already initialized
function initFirebase() {
    const firebaseConfig = {
        apiKey: "AIzaSyBdksK14GepHhzd7xpCYhtQ1xh03sLOAH0",
        authDomain: "kalyanx-replit.firebaseapp.com",
        projectId: "kalyanx-replit",
        storageBucket: "kalyanx-replit.appspot.com",
        messagingSenderId: "531899366727",
        appId: "1:531899366727:web:8ff86e1a4f29654ccb2062"
    };

    // Initialize Firebase if not already initialized
    if (typeof firebase !== 'undefined' && !firebase.apps?.length) {
        firebase.initializeApp(firebaseConfig);
        firebase.auth().setPersistence(firebase.auth.Auth.Persistence.LOCAL);
        return firebase;
    } else if (firebase.apps?.length) {
        return firebase.app();
    }
    console.error('Firebase SDK not loaded');
    return null;
}

// Initialize Firebase when DOM loads
document.addEventListener('DOMContentLoaded', initFirebase);

// Phone Authentication
// Send OTP via SMS
async function sendPhoneOTP(phoneNumber, recaptchaContainerId) {
  try {
    // Initialize reCAPTCHA
    window.recaptchaVerifier = new firebase.auth.RecaptchaVerifier(recaptchaContainerId, {
      'size': 'normal',
      'callback': (response) => {
        // reCAPTCHA solved, allow signInWithPhoneNumber.
        console.log('reCAPTCHA verified');
      },
      'expired-callback': () => {
        // Response expired. Ask user to solve reCAPTCHA again.
        console.log('reCAPTCHA expired');
      }
    });

    // Format phone number with country code if not present
    if (!phoneNumber.startsWith('+')) {
      // Default to India +91 if no country code
      phoneNumber = '+91' + phoneNumber;
    }

    // Send verification code
    const confirmationResult = await firebase.auth().signInWithPhoneNumber(
      phoneNumber, 
      window.recaptchaVerifier
    );

    // Save confirmation result globally
    window.confirmationResult = confirmationResult;
    return { success: true };
  } catch (error) {
    console.error('Error sending OTP:', error);
    if (window.recaptchaVerifier) {
      window.recaptchaVerifier.clear();
    }
    return { 
      success: false, 
      error: error.message 
    };
  }
}

// Verify OTP sent to phone
async function verifyPhoneOTP(code) {
  try {
    if (!window.confirmationResult) {
      throw new Error('No verification code was sent');
    }

    // Confirm the verification code
    const result = await window.confirmationResult.confirm(code);

    // User is signed in
    const user = result.user;
    const idToken = await user.getIdToken();

    return { 
      success: true, 
      idToken: idToken,
      user: {
        uid: user.uid,
        phoneNumber: user.phoneNumber
      }
    };
  } catch (error) {
    console.error('Error verifying code:', error);
    return { 
      success: false, 
      error: error.message 
    };
  }
}

// Email Authentication
// Send email verification link
async function sendEmailLink(email) {
  try {
    const actionCodeSettings = {
      // URL you want to redirect back to after email verification
      url: window.location.origin + '/verify-email-complete',
      handleCodeInApp: true
    };

    await firebase.auth().sendSignInLinkToEmail(email, actionCodeSettings);

    // Save the email to localStorage to remember what email was used for verification
    window.localStorage.setItem('emailForSignIn', email);

    return { success: true };
  } catch (error) {
    console.error('Error sending email link:', error);
    return { 
      success: false, 
      error: error.message 
    };
  }
}

// Check if current URL is email verification link and complete sign-in
async function completeEmailSignIn() {
  try {
    // Check if the link is a sign-in link
    if (!firebase.auth().isSignInWithEmailLink(window.location.href)) {
      return { 
        success: false, 
        error: 'Not a valid verification link' 
      };
    }

    // Get the email from localStorage that was saved when sending the link
    let email = window.localStorage.getItem('emailForSignIn');
    if (!email) {
      // If not found in storage, ask user for their email
      email = window.prompt('Please provide your email for confirmation');
    }

    // Complete the sign-in process
    const result = await firebase.auth().signInWithEmailLink(email, window.location.href);

    // Clear email from storage
    window.localStorage.removeItem('emailForSignIn');

    // Get ID token for backend verification
    const idToken = await result.user.getIdToken();

    return { 
      success: true, 
      idToken: idToken,
      user: {
        uid: result.user.uid,
        email: result.user.email
      }
    };
  } catch (error) {
    console.error('Error completing email verification:', error);
    return { 
      success: false, 
      error: error.message 
    };
  }
}

// Get current authenticated user
function getCurrentUser() {
    return firebase.auth().currentUser;
}

// Sign out
async function signOut() {
    try {
        await firebase.auth().signOut();
        return { success: true };
    } catch (error) {
        console.error('Error signing out:', error);
        return { 
            success: false, 
            error: error.message 
        };
    }
}

let googleProvider;
const getGoogleProvider = () => {
  if (!googleProvider) {
    googleProvider = new firebase.auth.GoogleAuthProvider();
    googleProvider.setCustomParameters({
      prompt: 'select_account'
    });
  }
  return googleProvider;
};