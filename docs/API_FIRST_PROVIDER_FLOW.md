# API-first provider flow

The system does not solve CAPTCHA, replay login sessions, scrape affiliate portals, or store tokens. When a portal triggers anti-bot, the state becomes `portal_fallback_blocked` and the campaign remains blocked.

Provider states:

- `api_ready`: official API authorization is complete and a secure runtime credential is available outside the repository.
- `user_authorization_required`: the user must complete one-time app/partner authorization and approve the requested scopes.
- `portal_fallback_blocked`: browser fallback is unavailable or anti-bot protected; no workaround is attempted.

One-time user action: open the official Shopee/Lazada developer/affiliate integration, authorize the local provider app, and confirm the requested link-generation and read-only metrics scopes. Never paste keys, cookies, OTPs, bank or tax data into the repository or chat.

After authorization, the automatic loop is:

`validated public product URL → official API link request → campaign affiliate URL update → redirect/tracking → official metrics sync → daily lead review`.

Until `api_ready`, source URLs can be researched and content drafted, but campaign activation is blocked.
