Kalyana Connection

OTP Delivery Setup (Phone SMS)

Your app now sends OTP using Twilio. If Twilio is not configured, the app shows a temporary OTP on screen for testing.

1) Add these environment variables in your .env file:

TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1XXXXXXXXXX

2) Restart the Flask server after updating .env.

3) Enter phone number in E.164 format when possible (example: +919876543210).
	- If you enter only 10 digits, the app auto-converts to +91 format.

4) If you are using Twilio Trial:
	- The destination phone number must be verified in Twilio console.
	- SMS may fail for unverified numbers.

5) If OTP does not arrive:
	- Check server terminal logs for Twilio error details.
	- The UI flash message shows whether SMS send failed and why.
"# KalyanaKonnection" 
