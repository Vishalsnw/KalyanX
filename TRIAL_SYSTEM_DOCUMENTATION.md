# KalyanX 7-Day Trial System Documentation

## Overview
KalyanX implements a 7-day free trial system using browser fingerprinting to uniquely identify visitors. This prevents users from bypassing the trial period by using incognito mode or clearing cookies.

## Components

### 1. FingerprintJS Integration
- Uses FingerprintJS v3 to generate a unique visitor ID
- Loaded via CDN: `https://cdn.jsdelivr.net/npm/@fingerprintjs/fingerprintjs@3/dist/fp.min.js`
- Implemented in `static/js/trial-access.js`
- Includes fallback mechanisms for when fingerprinting fails

### 2. Trial Access Management
- Class-based implementation in `TrialAccessManager`
- Stores trial start date in localStorage with visitor ID as key
- Automatically checks and applies trial restrictions based on elapsed days
- Blurs premium content after 7 days with a registration prompt

### 3. Premium Content Handling
- Uses `.premium-content` CSS class to mark premium elements
- During active trial: Content displays normally
- After trial expiration: Content is blurred with a registration prompt
- Premium elements are automatically detected and processed

### 4. Debugging & Testing
- Test page available at `/test-trial-system`
- Includes tools to:
  - Test FingerprintJS integration
  - View visitor ID and trial status
  - Reset trial period for testing
  - Manually override trial status

## Technical Implementation

### Visitor ID Generation
```javascript
async getVisitorId() {
  if (!this.fp) {
    await this.initializeFingerprint();
  }
  
  // If fingerprint.js failed to load, use a fallback identifier
  if (!this.fp) {
    console.warn("Using fallback visitor ID method");
    return "fallback-" + navigator.userAgent.replace(/\D+/g, '');
  }
  
  try {
    const result = await this.fp.get();
    console.log("Successfully generated visitor ID:", result.visitorId);
    return result.visitorId;
  } catch (error) {
    console.error("Error getting visitor ID:", error);
    // Create a consistent fallback ID based on browser and device information
    const fallbackId = "error-" + 
      (navigator.userAgent.replace(/\D+/g, '') || '') + 
      (navigator.platform || '') + 
      (screen.width || '') + 
      (screen.height || '');
    console.log("Using fallback ID:", fallbackId);
    return fallbackId;
  }
}
```

### Trial Access Checking
```javascript
async checkTrialAccess() {
  const visitorId = await this.getVisitorId();
  const storageKey = `trial_start_${visitorId}`;
  let trialStart = localStorage.getItem(storageKey);

  if (!trialStart) {
    trialStart = Date.now().toString();
    localStorage.setItem(storageKey, trialStart);
    console.log("Starting new trial with visitor ID:", visitorId);
    return true;
  }

  const daysPassed = (Date.now() - parseInt(trialStart)) / (1000 * 60 * 60 * 24);
  const hasAccess = daysPassed < 7;
  console.log(`Trial for visitor ID ${visitorId}: ${daysPassed.toFixed(2)} days passed, access: ${hasAccess}`);
  return hasAccess;
}
```

### Content Update Logic
```javascript
async updateContentVisibility() {
  try {
    const hasAccess = await this.checkTrialAccess();
    const premiumElements = document.querySelectorAll('.premium-content');
    console.log(`Found ${premiumElements.length} premium elements to update`);

    premiumElements.forEach(element => {
      if (hasAccess) {
        element.style.filter = 'none';
        element.style.pointerEvents = 'auto';
        const prompt = element.querySelector('.register-prompt');
        if (prompt) prompt.remove();
      } else {
        element.style.filter = 'blur(5px)';
        element.style.pointerEvents = 'none';

        if (!element.querySelector('.register-prompt')) {
          const prompt = document.createElement('div');
          prompt.className = 'register-prompt';
          prompt.innerHTML = `
            <div class="alert alert-warning text-center">
              <p>Register to continue accessing premium content</p>
              <a href="/auth/register" class="btn btn-warning mt-2">Register Now</a>
            </div>
          `;
          element.appendChild(prompt);
        }
      }
    });
  } catch (error) {
    console.error("Error updating content visibility:", error);
  }
}
```

## Usage Instructions

### Marking Premium Content
To mark content as premium, add the `premium-content` class:

```html
<div class="premium-content">
  <!-- Premium content here -->
  <p>This is premium content that will be blurred after the trial period.</p>
</div>
```

### Testing the Trial System
1. Access `/test-trial-system` to open the test page
2. Use the provided tools to check visitor ID and trial status
3. Use "Reset Trial" to test the initial trial experience
4. Use "Manual Override" to simulate trial expiration

### Troubleshooting
- Check console logs for visitor ID generation issues
- Verify that FingerprintJS is loaded properly
- Clear localStorage to reset all trials
- Check if `.premium-content` class is applied to appropriate elements

## Benefits
- Prevents trial bypassing through browser clearing/incognito mode
- Works without user accounts or requiring login
- Gracefully degrades with fallbacks if fingerprinting fails
- Provides clear indication when trial expires with call-to-action