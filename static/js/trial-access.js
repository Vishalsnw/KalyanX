/**
 * KalyanX Trial Access Manager
 * 
 * This class manages access to premium content based on a 7-day trial period.
 * It uses FingerprintJS to generate a unique visitor ID that persists across
 * browser sessions, even when cookies are cleared.
 */
class TrialAccessManager {
    constructor() {
        this.fp = null;
        this.initialized = false;
    }

    /**
     * Initialize the TrialAccessManager
     */
    async initialize() {
        try {
            await this.initializeFingerprint();
            this.initialized = true;
            await this.updateContentVisibility();
            return true;
        } catch (error) {
            console.error('Error initializing TrialAccessManager:', error);
            return false;
        }
    }

    /**
     * Initialize FingerprintJS
     */
    async initializeFingerprint() {
        try {
            // Check if FingerprintJS is already loaded
            if (window.FingerprintJS) {
                this.fp = await window.FingerprintJS.load();
                return true;
            }

            // Try to load FingerprintJS from CDN if it's not already loaded
            console.log('Loading FingerprintJS from CDN...');
            return new Promise((resolve, reject) => {
                const script = document.createElement('script');
                script.src = 'https://cdn.jsdelivr.net/npm/@fingerprintjs/fingerprintjs@3/dist/fp.min.js';
                script.onload = async () => {
                    try {
                        this.fp = await window.FingerprintJS.load();
                        resolve(true);
                    } catch (error) {
                        console.error('Error loading FingerprintJS:', error);
                        reject(error);
                    }
                };
                script.onerror = (error) => {
                    console.error('Failed to load FingerprintJS:', error);
                    reject(new Error('Failed to load FingerprintJS script'));
                };
                document.head.appendChild(script);
            });
        } catch (error) {
            console.error('Error initializing fingerprint:', error);
            return false;
        }
    }

    /**
     * Get a unique visitor ID using FingerprintJS
     * With fallback mechanisms if FingerprintJS fails
     */
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

    /**
     * Check if the user still has trial access
     * ALWAYS returns true for all users regardless of time - as requested
     */
    async checkTrialAccess() {
        const visitorId = await this.getVisitorId();
        const storageKey = `trial_start_${visitorId}`;
        let trialStart = localStorage.getItem(storageKey);

        if (!trialStart) {
            trialStart = Date.now().toString();
            localStorage.setItem(storageKey, trialStart);
            console.log("Starting new trial with visitor ID:", visitorId);
        }

        // ALWAYS return true regardless of time passed - all visitors always get access
        console.log(`Trial for visitor ID ${visitorId}: PERMANENT ACCESS ENABLED`);
        return true;
    }

    /**
     * Update the visibility of premium content based on trial status
     * Adds blur effect and prompt to register for expired trials
     * During trial period, premium content is visible without login requirement
     */
    async updateContentVisibility() {
        try {
            const hasAccess = await this.checkTrialAccess();
            const premiumElements = document.querySelectorAll('.premium-content');
            console.log(`Found ${premiumElements.length} premium elements to update`);

            premiumElements.forEach(element => {
                if (hasAccess) {
                    // During trial period - show premium content without restrictions
                    element.style.filter = 'none';
                    element.style.pointerEvents = 'auto';
                    
                    // Remove any existing prompts
                    const prompt = element.querySelector('.register-prompt');
                    if (prompt) prompt.remove();
                    
                    // Add trial badge if not already present
                    if (!element.querySelector('.trial-badge') && !document.querySelector('.hide-trial-badge')) {
                        const trialBadge = document.createElement('div');
                        trialBadge.className = 'trial-badge position-absolute top-0 end-0 m-2';
                        trialBadge.innerHTML = `
                            <span class="badge bg-warning">Free Trial</span>
                        `;
                        element.style.position = element.style.position || 'relative';
                        element.appendChild(trialBadge);
                    }
                } else {
                    // Trial expired - blur content and show register prompt
                    element.style.filter = 'blur(5px)';
                    element.style.pointerEvents = 'none';
                    
                    // Remove trial badge if present
                    const trialBadge = element.querySelector('.trial-badge');
                    if (trialBadge) trialBadge.remove();

                    // Add register prompt if not already present
                    if (!element.querySelector('.register-prompt')) {
                        const prompt = document.createElement('div');
                        prompt.className = 'register-prompt';
                        prompt.innerHTML = `
                            <div class="alert alert-warning text-center">
                                <p>Your free trial has expired</p>
                                <p class="small mb-2">Register to continue accessing premium content</p>
                                <div class="d-flex justify-content-center gap-2">
                                    <a href="/auth/register" class="btn btn-warning">Register Now</a>
                                    <a href="/auth/login" class="btn btn-outline-light">Login</a>
                                </div>
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
}

// Initialize trial access manager when the page loads
document.addEventListener('DOMContentLoaded', function() {
    const trialManager = new TrialAccessManager();
    trialManager.initialize();
});