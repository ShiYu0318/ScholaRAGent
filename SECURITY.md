# Security

## Reporting a vulnerability

Please do not open a public issue for a security problem. Use GitHub's private reporting
instead: **Security → Report a vulnerability** on this repository. Include what you found,
how to reproduce it, and what an attacker could do with it.

You can expect an acknowledgement within a week. Once a fix is released the report is
credited in the release notes, unless you prefer otherwise.

## Supported versions

Only the latest commit on `main` receives security fixes.

## Production checklist

Before exposing an instance to anyone but yourself:

- [ ] `APP_ENV=production`. The API then refuses to start with a missing or short
      `JWT_SECRET`, or with a wildcard CORS origin.
- [ ] `JWT_SECRET` is a random value of at least 32 characters (`openssl rand -hex 32`).
      Rotating it signs everyone out.
- [ ] Served over HTTPS, with `API_PUBLIC_URL` and `FRONTEND_URL` set to the `https://`
      origins. HSTS and the `Secure` flag on the OAuth cookie depend on this.
- [ ] `CORS_ORIGINS` lists only your frontend origin.
- [ ] `TRUST_PROXY=1` **only** when a reverse proxy you control sets `X-Forwarded-For`.
      Otherwise leave it off, or clients can forge their IP and bypass rate limits.
- [ ] `POSTGRES_PASSWORD` is set to a strong value when using the Postgres profile, and the
      database port is not published beyond localhost.
- [ ] Outbound traffic from the container is restricted at the network level if the host can
      reach internal services (see *Known limitations*).
- [ ] The `backend/data` volume is backed up; it holds the database and the vector index.
- [ ] Dependabot alerts and the CI dependency audit are enabled on your fork.

## What is defended, and how

The README's [Security section](README.md#security) describes the model in detail. In short:

| Threat | Defence |
| --- | --- |
| Password guessing, quota exhaustion | Per-IP and per-user sliding-window rate limits |
| Stolen session token | Password change requires the current password and revokes other tokens; sign-out-everywhere |
| OAuth account takeover and login CSRF | Linking only by provider-verified email; state bound to the browser by an HttpOnly nonce cookie |
| Server-side request forgery through RSS | Host resolution check on every redirect hop, response size cap, hardened XML parser |
| Prompt injection from retrieved content | Retrieved text is fenced and declared untrusted in every system prompt |
| Cross-user data access | Every query is scoped by owner; another user's id yields 404 |
| Cross-site scripting | Strict Content-Security-Policy, Markdown rendered without raw HTML, only http(s) links stored |
| Leaking internals | Generic error messages; details only in server logs; health endpoint minimal when anonymous |
| Oversized or malformed input | 1 MB body limit, length and count limits on every stored or prompted field |
| Vulnerable dependencies | `pip-audit` and `npm audit` in CI, weekly Dependabot updates |

## Known limitations

- **Rate limits are in-process.** With more than one API replica each replica counts
  separately; put a rate limiter in the reverse proxy or back it with a shared store.
- **DNS rebinding.** The SSRF check resolves the hostname and the HTTP client resolves it
  again when connecting. Closing that window entirely needs egress filtering.
- **Session tokens live in `localStorage`.** The CSP forbids inline and third-party scripts,
  which limits what an injected script could do, but a token in `localStorage` is readable by
  any script that does run. Moving to HttpOnly cookies would also require CSRF protection.
- **Prompt-injection defences are mitigations.** Fencing and instructions make injected text
  far less likely to be followed; they cannot guarantee it. Treat generated text as a draft.
- **The paper library is shared.** Anyone with an account can add papers and RSS items to it.
  Run a private instance if the corpus itself is sensitive.
