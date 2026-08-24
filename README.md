# email-verify-live

SMTP email verification worker for the B2B mailer pipeline. Runs on GitHub Actions every 20 minutes.

- Pulls pending candidates from the API, verifies via DNS MX + SMTP RCPT TO (with catch-all detection), posts results back.
- **No credentials in this repository.** The only secret is `API_SECRET`, stored in GitHub Actions secrets (Settings → Secrets and variables → Actions).
- The API endpoint IP is public infrastructure; it carries no credentials.
