# OneTagumVision Receipt Scanner (Android)

This is a lightweight Android companion app for Budget Monitoring receipt upload.

Flow:
1. Tap `Scan QR` in the app.
2. Scan the QR generated from the desktop expense form.
3. Tap `Capture Receipt`.
4. Tap `Upload Receipt`.

The app uploads directly to your existing Django endpoint:
- `/dashboard/finance/receipts/mobile-upload/api/`

## Prerequisites
- Android Studio (latest stable)
- Android SDK 34
- JDK 17

## Build (Debug APK)
1. Open the `mobile_app` folder in Android Studio.
2. Let Gradle sync finish.
3. Build APK:
   - `Build > Build Bundle(s) / APK(s) > Build APK(s)`
4. Install `app-debug.apk` on your phone.

## Local Testing
- Run Django with LAN bind:
  - `python manage.py runserver 0.0.0.0:8000`
- Ensure phone and laptop are on same Wi-Fi.
- Generate QR from desktop app and scan in this Android app.

## Security Notes
- For local tests, cleartext HTTP is enabled in this app.
- For production, use HTTPS domain in QR.
- Current backend validates:
  - signed temporary token
  - token expiry
  - file type
  - file size

