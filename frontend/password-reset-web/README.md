# KNU Campus password reset page

Deploy this directory as a static site on Vercel. The public backend base URL is configured in `config.js`:

`https://knu-campus-api-744461686522.asia-northeast3.run.app`

The page reads the `token` query parameter and posts it with the new password to `/auth/password-reset/confirm`. This URL is public API configuration, not a secret.

After the first Vercel deployment, set the backend's `PASSWORD_RESET_URL` environment variable to the deployed page URL (the root URL, without `?token=`), then deploy a new Cloud Run revision. The backend email code appends `?token=...` itself.
