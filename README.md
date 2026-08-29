# Dan_FX Trading Community Academy Platform

## Included
- Student registration and login
- Student dashboard
- Course catalog
- Enrollment workflow
- Classroom and lessons
- Lesson progress tracking
- Admin dashboard
- Add courses and lessons
- Student/enrollment management view
- SQLite database
- Responsive blue Dan_FX branding

## Run locally
1. Install Python 3.10+
2. Open a terminal in this folder
3. Run: `pip install -r requirements.txt`
4. Run: `python app.py`
5. Open: http://127.0.0.1:5000

## Default admin account
Email: admin@danfx.local
Password: ChangeMe123!

CHANGE THIS PASSWORD AND SECRET_KEY BEFORE DEPLOYMENT.

## Payments
The current checkout demonstrates the full enrollment flow but intentionally does NOT process real money.
For production, integrate one provider:
- Stripe
- Paystack
- Flutterwave

Important: payment activation must happen only after server-side webhook verification.

## Production recommendations
- PostgreSQL instead of SQLite
- HTTPS
- Environment variables for SECRET_KEY and payment keys
- Email verification/reset
- CSRF protection
- Object storage for course media
- Payment webhooks
- Audit logging
