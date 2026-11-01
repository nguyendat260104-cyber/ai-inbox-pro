# Landing CTA and responsive QA — 2026-10-20

## Slice brief

- **Goal:** make the landing page's demo action useful without sending visitors to a disconnected page.
- **Audience / need:** a retail operator should be able to preview how the sales assistant behaves, then deliberately open the full workspace when ready.
- **Flow:** `Thử hội thoại mẫu` opens a local, clearly labeled sample assistant in place; a suggested question produces a sample answer; dismissing the panel returns focus to the initiating control. `Mở Command Center` remains a separate, explicit route to the workspace. `Xem cách hệ thống vận hành` remains an in-page jump to the four-step process.
- **States:** closed, open, selected question / answer, close button, Escape dismissal. Every sample response disclaims live inventory, AI, and human handoff.
- **Responsive:** desktop, 1024px tablet, and 390px narrow mobile. Keep the channel sticker rail in a reserved viewport gutter only while adjacent to the product proof.
- **Risk:** presenting sample content as a real integration or an active AI agent. Keep visible sample-data language and avoid real system actions.
- **Acceptance:** no needless route change from the inline assistant CTA; meaningful route destinations for the full storefront and workspace; no horizontal overflow; readable product proof; keyboard-operable open, prompt, close, Escape, and focus return.

## Reference basis

The existing reference audit covers official public product pages for Intercom, Zendesk, Crisp, Tidio, and HubSpot; the supplementary research notes cover Bizfly and SaleAI. The applied pattern here is a product-led, in-context preview with a clearly distinguished next step—not an assumption about any vendor's internal implementation. See `20261020-ai-inbox-ux-reference-audit.md` and `20261020-saleai-reference-notes.md`.

## Changes

- Replaced the header's `Xem Demo Store` cross-page CTA with `Thử hội thoại mẫu`, which opens the same scripted, in-page assistant as the dock robot. The full sample storefront remains available through the footer's `Storefront` link.
- Wired both launch controls to one panel; both expose synchronized `aria-expanded`, opening moves focus to the first prompt, close and Escape return focus to the initiating control, and suggested answers are announced via `aria-live`.
- Added an anchor offset for the sticky, two-row mobile header so the process section heading is no longer hidden behind navigation.
- Made the sticky navigation surface opaque so underlying page text does not bleed through while scrolling.
- Kept `Mở Command Center` separate and verified that it opens `/admin`; verified the full storefront link opens `/demo` and renders the sample fashion storefront.
- Reserved a fixed right-side gutter for the vertical Messenger / Zalo / Facebook rail. The rail hides when the product mock is not alongside it or when it would otherwise obstruct content. Removed the dock's ancestor filter, which had accidentally made the supposedly fixed rail position relative to the dock.
- Added reduced-motion handling for the CTA, prompt controls, channel rail, ticker, and page scrolling.

## Acceptance evidence

- **1440 × 900:** desktop screenshot reviewed. Hero copy and product proof remain distinct; the product stage ends at x=1269.8 and the rail begins at x=1292.2 (22.4px gap). Rail appears only alongside the mock. Document scroll width is 1425px against a 1440px viewport; no horizontal overflow.
- **1024 × 768:** tablet screenshot reviewed. Centered hero copy and product proof stack vertically; stage begins below the copy (y≈704), not over it. The rail stays hidden until the mock enters its vertical zone. Document scroll width is 1009px against a 1024px viewport.
- **Tablet journey grid follow-up:** the first tablet review exposed all four process steps squeezed into a single row despite the narrower viewport. Added a two-column grid at widths up to 1100px; screenshot re-review at 1024px shows a balanced 2×2 layout with complete headings and readable descriptions. Mobile remains a single-column stack.
- **768 × 900 narrow-tablet follow-up:** review exposed the sticky nav forcing brand, four links, and both actions into one crowded 74px row, with wrapped labels. The 701–850px layout now uses a deliberate two-row nav (brand/actions, then centered route links); measured height is 98px, and anchor offset is 132px. The process grid remains 2×2 with 337px content columns at this viewport, clear heading placement below the nav, and no horizontal overflow.
- **390 × 844:** mobile screenshot reviewed. Headline is 34px and two lines; product proof becomes a single readable conversation column. Stage x=20–259.2 and rail x=272.6–315.2 (13.4px reserved gap) when scrolled alongside it. Document scroll width is 375px against a 390px viewport.
- **390 × 844, assistant open:** header CTA opens the panel without changing route; the panel measures x=4.8–363.2 and y=450.4–782, staying inside the viewport. The panel's visible sample disclaimer is present.
- **Mobile in-page anchor:** the process section starts at y≈146px below the 143.7px sticky header; the heading is fully visible rather than obscured.
- **Lower-page mobile review:** the four process steps stack in order, the outcome list and closing CTA remain readable, and footer links stay clear of the fixed assistant button. No horizontal overflow observed at the bottom of the page.
- **CTA behavior:** `Thử hội thoại mẫu` keeps the URL at `/landing`, opens the panel, and synchronizes both launch controls' expanded state. Selecting `Kiểm tra size L` adds the prompt and sample-only response. Close button and Escape both dismiss the panel and restore focus; tested from both header and dock launchers.
- **Navigation:** `Mở Command Center` loaded `/admin` with the AI Inbox Command Center title. Storefront link loaded `/demo` with the Fashion Young Studio storefront title. The in-page process CTA updates the URL to `#how-it-works` and scrolls to the four-step section.
- **Route sweep:** `/features`, `/solutions`, `/pricing`, `/resources`, `/demo`, and `/admin` all loaded distinct expected page titles and headings; no route fell back to Landing.
- **Keyboard:** initial `Tab` focus reaches the brand link with a visible blue focus outline. The header demo button opens with `Enter`; prompt receives focus; `Escape` closes and returns focus to the header button.
- **Contrast spot-check:** rendered computed colors against the nearest opaque ancestor background measured 17.13:1 for the hero headline, 6.13:1 for the hero lede, 4.84:1 for the primary CTA, 7.82:1 for nav links, 17.36:1 for the process heading, and 9.98:1 for process descriptions. These representative pairs pass WCAG AA contrast; this is not an exhaustive audit of every state or label.
- **Motion source review:** entrance and mascot motion are gated behind `prefers-reduced-motion: no-preference`; the dock animation, ticker, stickers, and smooth scrolling have reduced-motion overrides in the shipped CSS. Browser-level reduced-motion emulation remains untested.
- **Runtime:** browser console warning/error log returned empty during these checks.

## Still open — do not score or advance

- This is a focused conversion/hero and behavior review, not a complete production acceptance of every Landing section. Tablet review of the process, human-control, benefits, and closing sections at 768px is recorded; exhaustive contrast audit, resource verification against a fresh process, 1024px lower-section recheck, and browser-level reduced-motion emulation remain open.
- No quality score is claimed. Continue the Landing slice until every acceptance category in the quality gate passes; do not start the next page yet.
- The assistant is a deterministic local sample, not a real model, inventory lookup, channel connection, or human handoff.

## Responsive follow-up — 2026-10-20 15:55

- **768 × 900:** a live screenshot exposed the three-column product mock collapsing the conversation to roughly 110px and stretching the panel to over 1,600px tall. The tablet layout now removes the low-priority queue and uses a readable conversation-plus-customer-context split. After reload, the mock measures 555px tall with 365px/190px columns; document width remains within the viewport. The sticky nav is an intentional two-row layout (brand/primary action, then route links), 97px high.
- **390 × 844:** the fixed channel rail is shown only while it can sit beside the product preview without intersecting hero copy; it stays hidden over page text and outside the product-preview region. Messenger, Zalo and Facebook marks remain a vertical rail. The mobile nav uses two rows, 92px high, with the four route links on one horizontal rail. Document layout width remains 375px against a 390px viewport (no horizontal overflow).
- **Mobile assistant panel:** opened from the dock. The panel measures x=14.8–363.2 and y=236.5–782, fits inside the 390×844 viewport, shows all three scenario choices and the explicit local-simulation disclaimer. No live backend or real stock/order action is implied.
- **1440 × 900:** after the responsive CSS change, the product proof measures 700px wide and 554.5px high; the vertical channel rail begins 22.4px after the mock. Mascot image assets load successfully, and the document width is 1425px against a 1440px viewport.
- **768px anchor:** the in-page “Xem cách hệ thống vận hành” link updates the URL to `#how-it-works`; after the smooth scroll settles, the section begins at y=132px below the 97px sticky navigation.
- **768px lower sections:** reviewed the 2×2 process grid, stacked human-control panel, outcome list, and closing CTA. Headings and body copy remain visible; no horizontal overflow appeared. The lower tablet section spacing is still generous and remains part of the visual-quality review rather than being counted as a pass by default.
- **1024 × 768 / 900 × 900:** product proof remains a three-column preview with legible conversation and context; at 900px the queue collapses to preserve the conversation. Measured mock heights were 555px at 1024 and 516px at 900; document width remained within each viewport.
- **Resource diagnostic:** the current process serving port 8083 returns 200 for the mascot PNG and brand SVG but labels both `text/html`; the visible PNG happens to render, while embedded channel-mark data still displays. `ai_inbox/api/server.py` contains the correct extension-based/guessed MIME mapping, but the already-running process has not been restarted, so this live-server check is not a pass and should be rechecked after a safe restart. Startup calls database initialization, so I did not restart it during this review.
- These fixes close the specific narrow-tablet mock and mobile copy-overlap defects. The full Landing gate is still open: exhaustive contrast audit, resource verification against a fresh process, 1024px lower-section recheck, and browser-level reduced-motion emulation remain outstanding. No overall score is claimed.

## QA follow-up — 2026-10-20 23:16 Asia/Saigon

- **Fresh-process asset/MIME check:** started the current server handler on an isolated local port with its database-initialization function disabled, so no project database was opened or changed. `GET /landing` returned `200 text/html; charset=utf-8`; `/web/assets/ai-orbit-mascot.png` returned `200 image/png`; `/web/assets/brand-facebook.svg` returned `200 image/svg+xml`; `/web/landing-art-direction.css` returned `200 text/css; charset=utf-8`; `/web/assistant-demo.js` returned `200 application/javascript; charset=utf-8`. The isolated process was stopped after verification. The previous 8083 process still has the separately recorded stale MIME response; it was not restarted.
- **Contrast screening:** a rendered-DOM scan examined 130 visible text-bearing elements after excluding the decorative channel-mark rail. It found five low-contrast supporting labels in the product mock. Darkened the conversation metadata, catalog tag, composer helper and agent-trace text, and increased the small metadata sizes. Re-scan found no remaining textual failures; two remaining matches are letter glyphs (`Z`, `f`) attached to channel-mark icons styled with `font-size: 0`, not readable text labels. This is a DOM-based screening using nearest opaque ancestor colors, not a substitute for manual review of every translucent/hover/focus state.
- **1024px lower-page review:** set the browser viewport to 1024×768; document width measured 1009px, so no horizontal overflow. Reviewed the human-control/AI activity region and closing CTA at the tablet width. Control section height measured 855px and CTA section 527px; content remained within viewport width. This is a visual spot review, not a full audit of every state.
- **Browser diagnostics:** warning/error log query returned no entries for the checked page session. The responsive-motion emulation remains unavailable in the current browser controls; source rules have been reviewed but runtime emulation is still unverified.
- **Still open:** manual contrast checks for interactive/focus/hover and all states; runtime reduced-motion emulation; remaining route and state coverage; qualitative review of the full Landing composition. No slice score is claimed and no page transition is authorized.

## Interaction follow-up — 2026-10-20 23:22 Asia/Saigon

- **Keyboard focus:** first Tab focuses the brand link with a visible `2.4px` blue `:focus-visible` outline (`#465fff`).
- **Assistant launch/dismissal:** pressing Enter on `Thử hội thoại mẫu` opens the sample panel without changing `/landing`, synchronizes `aria-expanded=true`, and makes the panel visible. Escape closes it, restores `aria-expanded=false`, hides the panel, and returns focus to the invoking header button. Browser console warning/error query remained empty in this session.
- **Still open:** contrast/focus review of the remaining controls and hover states, browser-level reduced-motion emulation, and full-page visual/route/state acceptance. No overall score is claimed.

## Full focus-order follow-up — 2026-10-21 Asia/Saigon

- **Complete keyboard order:** traversed every interactive Landing control in document order in four small batches: brand, four primary navigation links, header sample-assistant button, header Command Center CTA, hero CTAs, all product-proof links, control-section links, closing CTA, assistant launcher, and all three footer links.
- **Visible focus:** every link and button exposes a visible solid focus ring. Rendered outlines measured `2.4px` in the browser, using the blue focus colors `rgb(70, 95, 255)` or `rgb(36, 63, 224)` depending on the control. No focused control was hidden, clipped, or zero-sized.
- **Focus loop:** after the last footer link, focus returns to the document before restarting at the brand; no unexpected focus trap was observed while the assistant was closed.
- **Runtime diagnostics:** the browser warning/error log remained empty after the full focus traversal.
- **Hover/source review:** the Landing hover rules do not lower text contrast: navigation hover changes text to the brand blue on white, primary CTA hover changes elevation only, prompt hover keeps dark text on a lighter surface, and the remaining hover treatments are transform/background accents. Runtime pointer-state inspection is still desirable as part of the final qualitative pass.
- **Still open:** browser-level reduced-motion emulation and the final full-composition qualitative review. No overall score is claimed yet.

## Channel rail composition fix — 2026-10-21 Asia/Saigon

- **Defect found:** the floating Messenger / Zalo / Facebook rail remained rendered over the dark four-step process section. JavaScript correctly removed `channel-rail-visible` outside the product-proof region, but a later unconditional rule in `orbit-dock.css` forced `visibility: visible` and `opacity: 1`, overriding the state contract.
- **Fix:** removed the unconditional visibility override. The rail now follows the existing geometry gate in `assistant-demo.js`: it appears only when vertically aligned with the hero product proof, remains outside the product panel, and does not overlap hero copy.
- **Runtime evidence at 1280 × 720:** at page top, the hero product proof measured x=543.8–1119.8 and the rail measured x=1132.2 with `channel-rail-visible=true`; the rail was visible beside—not on top of—the product proof. At scrollY=780, the rail reported `channel-rail-visible=false`, `visibility:hidden`, and `opacity:0`; screenshot review confirmed the process heading and all four steps were unobstructed.
- **Diagnostics:** no browser warning/error entries appeared after reload, top-state validation, and process-section validation.
- **Still open:** final full-page qualitative review and browser-level reduced-motion emulation. No overall score is claimed yet.

## Composition density and reduced-motion runtime — 2026-10-21 Asia/Saigon

- **Full-page composition:** reviewed a fresh 1280px full-page capture from hero through footer after the channel-rail correction. The rail no longer appears over the process, human-control, outcomes, or closing sections. The visual sequence now alternates white product proof, dark decision flow, light human-control evidence, editorial operating principles, and a dark closing action without an obstructive overlay.
- **Outcomes section refinement:** the operating-benefits section was visually underfilled and read like a heading beside a generic list. Added a concise operating thesis and three explicit guardrails—visible data source, approval-required actions, and contextual handoff—without introducing another card grid. Increased supporting label, benefit-heading, and benefit-body sizes to restore readable hierarchy.
- **Responsive evidence:** at 1280×720 the refined section remains a balanced two-column editorial layout with no horizontal overflow. At 768×900 it stacks into a clear narrative followed by three separated outcomes; document width remained 753px inside a 768px viewport. At 390×844 it remains a single readable column, the three guardrails wrap cleanly, the floating channel rail stays hidden, and document width remained 375px inside a 390px viewport.
- **Reduced-motion runtime:** added `scripts/qa_reduced_motion.ps1`, which launches the installed Edge headlessly with `--force-prefers-reduced-motion=reduce`, waits for page and font load, and inspects computed styles through the local DevTools endpoint. The first run exposed smooth scrolling still enabled; strengthened the reduced-motion cascade and reran the probe. Final result: `reduced=true`, `scrollBehavior=auto`, `heroAnimation=none`, `railTransition=0s`, and `mascotAnimation=none`.
- **Diagnostics:** local browser console warning/error log remained empty after restoring the default viewport. The page measured 1265px document width inside the 1280px viewport.
- **Still open:** rerun the final route/CTA/state sweep against the current composition, reconcile the evidence into the quality rubric, and only then decide whether Landing crosses the >90 gate.
