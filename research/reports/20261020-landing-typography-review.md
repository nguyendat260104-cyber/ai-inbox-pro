# Landing typography and visual QA — 2026-10-20

## Slice brief

- **Goal:** make the Vietnamese hero easier to scan and more composed without letting the product mock collide with the message.
- **Scope:** Landing type system, hero sizing/spacing, restrained interaction depth, and desktop visual review. No other page is approved by this work.
- **Acceptance:** readable Vietnamese typography; clear heading/body hierarchy; no overlap at the observed desktop viewport; visible keyboard focus; reduced-motion fallback; existing CTA/link labels remain intact.

## Changes in this pass

- Replaced the mixed Manrope/Newsreader headline treatment with a consistent Inter sans-serif family and a blue, semibold second phrase. This removes the visually inconsistent serif line and makes the headline more legible.
- Tightened the hero promise to “AI xử lý hội thoại. Sale chốt đúng lúc.”; the desktop screenshot confirms the blue phrase now holds together on one line instead of leaving “lúc.” isolated.
- Corrected the Google Fonts request to valid Inter weights (400, 500, 600, 700, 800); browser screenshot after reload shows the sans-serif face applied.
- Reduced the desktop hero headline maximum to 50px in the 1101–1340px range and narrowed the product stage to 53vw to preserve separation from the copy.
- Kept interaction layers restrained: nav underline, a small product-surface lift/shadow, process-step hover, explicit focus ring, and reduced-motion overrides.

## Local evidence

- `http://127.0.0.1:8083/landing` reloaded after the change. At the available ~1265px desktop viewport, the headline no longer uses the serif accent, fits the left column, and does not overlap the product mock.
- The dark process section shows four ordered steps with readable contrast and a single-column section intro.
- The human-control section presents the mock activity log and an explicit approval/handoff state; benefits and final CTA remain present in the accessibility tree.
- Keyboard `Tab` reaches the brand link with a visible blue focus outline.
- The accessibility tree confirms all main navigation/CTA destinations still point to `/features`, `/solutions`, `/pricing`, `/resources`, `/demo`, or `/admin` as expected.
- Activated the hero's in-page CTA; it navigates to `http://127.0.0.1:8083/landing#how-it-works` and lands on the process section.
- Follow-up desktop review at the available ~1265px viewport caught the fixed channel dock overlapping the sample customer panel. The hero preview was narrowed and its channel columns rebalanced; the latest screenshot shows a clear gap between the product surface and the vertical Messenger/Zalo/Facebook rail.
- Replaced the letter/envelope-like header mark with the brand lightning mark; confirmed visually after reloading the local page.
- The floating channel rail is visible and vertically ordered in the accessibility tree. Its labels are Messenger, Zalo OA, and Facebook.
- Replaced the robot's misleading cross-page link with an inline, dismissible sample assistant. Verified that opening it keeps the URL on `/landing`, the three suggested questions add the chosen prompt and a clearly marked mock response, the panel announces updates through `aria-live`, and the close control returns focus to the trigger.
- Rechecked the narrower ~637px viewport: the rail no longer covers the sample conversation, and the assistant panel fits within the viewport. This is not a 390px phone-sized verification.

## Open acceptance items — do not score or advance

- Tablet and 390px mobile screenshots have not been captured in an actual responsive viewport in this pass.
- Console/network diagnostics are unavailable through the current browser interface; CSS loading and runtime errors therefore remain unverified.
- Keyboard Escape close behavior is implemented but was not verifiable through the available browser keyboard-control interface.
- Reduced-motion behavior is present in CSS, but has not been exercised with an OS/browser reduced-motion setting.
- The floating assistant is a local scripted prototype only; it does not call an AI model, external channel, real catalog, inventory, or human handoff.
- The main visual and interaction checks are partial-page desktop checks, not full-route sign-off. Do not label Landing production-ready.
