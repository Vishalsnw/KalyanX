// Premium membership status checking
// This script handles premium status checking for Firebase users

/**
 * Check if a user is a premium member
 * @returns {Promise<boolean>} Whether the user has active premium status
 */
async function checkPremiumStatus() {
  return new Promise((resolve) => {
    // Check if Firebase is loaded
    if (typeof firebase === 'undefined') {
      console.error('Firebase is not loaded');
      resolve(false);
      return;
    }

    // Check for authenticated user
    const auth = firebase.auth();
    const currentUser = auth.currentUser;

    if (!currentUser) {
      console.log('No authenticated user found');
      resolve(false);
      return;
    }

    // Get Firestore reference
    const db = firebase.firestore();
    const userDoc = db.collection('users').doc(currentUser.uid);

    // Get user data
    userDoc.get().then((doc) => {
      if (doc.exists) {
        const userData = doc.data();
        
        // Check premium status and expiry date
        const isPremium = userData.isPremium === true;
        const expiryDate = userData.premiumExpiryDate;
        const currentTime = Date.now();
        
        // User is premium if they have premium status and the expiry date is in the future
        const hasPremium = isPremium && expiryDate && expiryDate > currentTime;
        
        console.log('Premium status:', hasPremium);
        resolve(hasPremium);
      } else {
        // Create user document if it doesn't exist
        userDoc.set({
          email: currentUser.email,
          displayName: currentUser.displayName,
          photoURL: currentUser.photoURL,
          isPremium: false,
          createdAt: Date.now()
        }).then(() => {
          console.log('Created new user document');
          resolve(false);
        }).catch(error => {
          console.error('Error creating user document:', error);
          resolve(false);
        });
      }
    }).catch(error => {
      console.error('Error checking premium status:', error);
      resolve(false);
    });
  });
}

/**
 * Update UI based on premium status
 * @param {boolean} isPremium Whether the user has premium status
 */
function updateUIForPremiumStatus(isPremium) {
  // Select all elements with premium-content class
  const premiumElements = document.querySelectorAll('.premium-content');
  const nonPremiumElements = document.querySelectorAll('.non-premium-content');
  
  if (isPremium) {
    // Show premium content
    premiumElements.forEach(element => {
      element.style.display = '';
    });
    
    // Hide non-premium content
    nonPremiumElements.forEach(element => {
      element.style.display = 'none';
    });
    
    console.log('UI updated for premium user');
  } else {
    // Hide premium content
    premiumElements.forEach(element => {
      element.style.display = 'none';
    });
    
    // Show non-premium content
    nonPremiumElements.forEach(element => {
      element.style.display = '';
    });
    
    console.log('UI updated for non-premium user');
  }
}

/**
 * Initialize premium features
 */
function initPremiumFeatures() {
  // Listen for auth state changes
  firebase.auth().onAuthStateChanged(user => {
    if (user) {
      // Check premium status when user is signed in
      checkPremiumStatus().then(isPremium => {
        updateUIForPremiumStatus(isPremium);
      });
    } else {
      // User is signed out, update UI accordingly
      updateUIForPremiumStatus(false);
    }
  });
}

// Initialize when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  // Wait for Firebase to be initialized first
  if (typeof firebase !== 'undefined') {
    initPremiumFeatures();
  } else {
    // If Firebase isn't loaded yet, wait for the custom event
    document.addEventListener('firebase-initialized', initPremiumFeatures);
  }
});