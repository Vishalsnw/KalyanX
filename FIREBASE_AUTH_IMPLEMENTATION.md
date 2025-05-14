# Firebase Authentication Backend Implementation Guide

This document provides instructions for setting up and configuring Firebase Authentication for KalyanX's backend authentication system.

## Overview

KalyanX uses Firebase Authentication as a reliable, secure backend method for user authentication verification. This implementation provides:

1. More reliable backend SMS/email verification
2. Enhanced security with token-based validation
3. Single Sign-On with Google accounts
4. Cross-platform authentication support

## Prerequisites

Before you can use Firebase Authentication with KalyanX, you need:

1. A Firebase project
2. Firebase Authentication enabled in your project
3. Environment variables set up with your Firebase credentials

## Setup Instructions

### Step 1: Create a Firebase Project

1. Go to the [Firebase Console](https://console.firebase.google.com/)
2. Click "Add project" to create a new project
3. Follow the setup wizard to create your project
4. Once created, click on your project to open the dashboard

### Step 2: Enable Authentication Methods

1. In the Firebase console, navigate to "Authentication" in the left sidebar
2. Click on the "Sign-in method" tab
3. Enable the authentication methods you want to use:
   - Email/Password
   - Phone
   - Google

### Step 3: Add KalyanX Application to Firebase

1. In the Firebase console, click on "Project Overview"
2. Click "Add app" and select the Web platform (</> icon)
3. Name your app (e.g., "KalyanX Web")
4. Register the app
5. Firebase will provide configuration details including apiKey, authDomain, etc.

### Step 4: Configure Authorized Domains (CRITICAL)

1. In the Firebase console, go to "Authentication" → "Settings" → "Authorized domains"
2. Add your domain(s) where KalyanX is hosted:
   - During development: Add your Replit URL (e.g., `kalyan-x.repl.co`)
   - After deployment: Add your custom domain or replit.app domain
3. **WARNING**: Without this step, Google Sign-in will NOT work!
4. This configuration allows Firebase Authentication to redirect back to your app after Google Sign-in

### Step 5: Add Firebase Config to KalyanX

1. Collect the following credentials from your Firebase project:
   - API Key
   - Project ID
   - App ID

2. Set these as environment variables in your KalyanX deployment:
   ```
   FIREBASE_API_KEY=your_api_key
   FIREBASE_PROJECT_ID=your_project_id
   FIREBASE_APP_ID=your_app_id
   ```

## How Authentication Works

KalyanX implements a dual authentication system:

1. **Firebase Authentication** (primary method):
   - User authenticates through Firebase (email, phone, or social)
   - Firebase provides a secure token
   - KalyanX backend verifies this token
   - User is registered/logged in based on the verified information

2. **Legacy Authentication** (fallback method):
   - Direct email or mobile verification
   - OTP verification handled by KalyanX servers

Firebase Authentication is recommended for its reliability and security.

## User Experience

The Firebase Authentication is completely invisible to the end user:

1. User enters their email/mobile and completes verification normally through the KalyanX interface
2. Behind the scenes, KalyanX verifies the user through Firebase 
3. The user is authenticated without ever seeing or interacting with Firebase directly
4. User is redirected to the dashboard with a seamless experience

## Troubleshooting

### Common Issues

1. **Backend authentication fails**
   - Check server logs for Firebase-related errors
   - Verify environment variables are set correctly

2. **Authentication fails**
   - Verify your domain is in the authorized domains list
   - Check if Firebase services are enabled

3. **Token verification fails**
   - Check Firebase Admin SDK initialization
   - Verify project settings match between client and server

## Security Considerations

1. Keep your Firebase credentials secure and never expose them in client-side code
2. Verify tokens on the server side before trusting user information
3. Implement proper session management after authentication
4. Set appropriate security rules in Firebase

## Additional Resources

- [Firebase Authentication Documentation](https://firebase.google.com/docs/auth)
- [Firebase Security Rules](https://firebase.google.com/docs/rules)
- [FirebaseUI for Web](https://firebase.google.com/docs/auth/web/firebaseui)