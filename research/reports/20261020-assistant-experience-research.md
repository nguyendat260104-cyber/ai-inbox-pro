# Landing assistant experience — research and acceptance brief

## Scope

Upgrade only the landing-page assistant and adjacent channel-mark dock. The goal is to let a prospective buyer experience the product's sales workflow, rather than being redirected by a decorative demo button. There is no AI backend, catalog connection, inventory service, live channel connection, human routing, or official brand kit yet.

## Public product research

The notes below describe public product pages or official help documentation only. They do not claim knowledge of vendors' internal implementation.

| Product | Publicly documented pattern | Application to this local prototype |
| --- | --- | --- |
| Intercom Fin | The official workflow docs describe message steps, information collection, data connectors, configurable handover, and the ability to preview before launch. Its product updates describe source links inside replies and conversational escalation. | Use a short, visible intent → catalog → recommendation → handoff story, and label all local data as a simulation. Do not imply the prototype has these integrations. |
| Zendesk AI agents | Official docs describe trusted knowledge sources, channel configuration, topic/use-case flows, activation, monitoring, and a separate handoff/handback model. | Make the data/source and the transition to a human explicit; do not imply a human has been notified. |
| Crisp / Hugo | Official inbox documentation describes AI suggestions inside the agent inbox, customer context in a sidebar, and routing based on intent to a team inbox or operator. | Show the answer source and a compact handoff brief, not only a generic answer bubble. |
| HubSpot Customer Agent | Its public product page describes taking actions in CRM, testing before going live, controlled rollout, and team handoff with context. | Keep the local experience testable and make the next step inspectable; avoid claiming live CRM action or production readiness. |
| Tidio Lyro | Tidio's official materials describe AI responses grounded in curated Q&A / website data sources and a chat experience; public documentation frames answers around added knowledge. | Demonstrate that the sample answer references a named sample catalog, not an invented live lookup. |

### Evidence links

- [Intercom — Fin workflow and handover](https://www.intercom.com/help/en/articles/10032299-use-fin-ai-agent-in-workflows)
- [Intercom — source links and conversational escalation update](https://www.intercom.com/changes/en/94618-fin-is-more-conversational)
- [Zendesk — getting started with customer-service AI agents](https://support.zendesk.com/hc/en-us/articles/8724978128282-Getting-started-with-AI-agents-for-customer-service)
- [Zendesk — handoff and handback](https://support.zendesk.com/hc/en-us/articles/4408824482586-Managing-conversation-handoff-and-handback)
- [Crisp — inbox context and AI suggestions](https://help.crisp.chat/en/article/getting-started-with-the-crisp-inbox-1a9mi26/)
- [Crisp — Hugo routing and escalation](https://help.crisp.chat/en/article/how-does-hugo-routing-work-47o06k/)
- [HubSpot — Customer Agent](https://www.hubspot.com/products/artificial-intelligence/ai-customer-service-agent)
- [Tidio — FAQ and knowledge sources for Lyro](https://www.tidio.com/faq/)
- [Simple Icons — source repository and license](https://github.com/simple-icons/simple-icons)

## Vertical-slice brief

- **Audience / job:** an ecommerce operator considering the solution should see how an AI sales workflow qualifies intent, checks product facts, recommends a next action, and prepares a human handoff.
- **Pain:** the existing floating assistant looked like a generic bot button, used crude letter marks, and returned three disconnected canned lines without a workflow or evidence.
- **Experience:** open in place → choose a size/stock, price, purchase, or human-help scenario (or enter a short question) → see a staged workflow trace → receive a sample answer with its source → optionally inspect a handoff brief → choose to restart or open the Admin sample.
- **Truth boundaries:** label the agent and catalog as a local simulation; never claim model inference, live stock, real channel status, actual human notification, order creation, or context transfer to Admin.
- **Visual direction:** use the custom project mascot and local vector brand marks from Simple Icons; maintain a compact vertical rail only when it does not cover page content. Use strong Manrope weights and clean density, not more decorative effects.
- **States:** closed/open, input/quick prompt, staged processing, grounded sample answer, handoff preview, fallback for unsupported requests, restart, close/Escape and focus return.
- **Responsive:** desktop, 768px tablet, 390px and 360px mobile; panel must remain inside viewport and keyboard-usable with no horizontal overflow.
- **Accessibility:** semantic form/input, live response region and separate processing status, accessible channel labels, visible focus, Escape dismissal/focus return, reduced-motion behavior, and text contrast.
- **Risks:** the local scenario interpreter is deterministic and narrow; the 50-unit and 250,000đ values are sample-only; the Admin route does not receive conversation state.
- **Acceptance:** verify the main prompts and free-text branches, source labels and handoff disclaimers; run local route/asset checks; inspect screenshots at all target widths; inspect console/errors; validate focus/reduced motion and no horizontal overflow. Do not score or advance until every acceptance point is checked.

## Implementation / validation record

### Local acceptance run — assistant and channel dock

- Reviewed the live Landing page at 1440×900, 768×900, 390×844, and 360×640. The document did not horizontally overflow at any checked width; at 360×640 the open panel remained within the viewport (x=14.8, right=332.8, bottom=578 in a 345 px browser content area) and its own scroll height matched its client height.
- Reduced the initial empty conversation area from 220 px to 110 px; it expands for an active exchange and remains internally scrollable. This cuts unnecessary blank space while retaining room for a longer response.
- Visually confirmed the vertical Messenger, Zalo, and Facebook marks and the custom mascot on desktop; each channel mark uses the corresponding official Simple Icons vector path embedded locally in CSS. The visible mascot image loaded at 1254×1254.
- Exercised size/stock, price, purchase-intent handoff, human-request handoff, and unsupported-question branches. The sample catalog answers identify their source and sample-only values. Both handoff paths say no real employee was notified; order intent produces a draft only, with no message or order sent.
- Checked the top “Thử hội thoại mẫu” control opens the assistant in place, the close/Escape paths close it, Escape restores focus to the invoking control, reset clears the conversation, and the active workflow step is exposed using `aria-current="step"`. Checked image roles/labels, the live conversation log, and the explicit no-backend disclaimer.
- Browser console returned no warning/error entries. The local assistant script contains no API endpoint, `fetch`, or XHR call; its responses are deterministic browser-side scenarios.
- Increased small labels and darkened muted text to improve legibility. Contrast measured against white: `#66758b` = 4.69:1 and `#59677f` = 5.72:1. Reduced-motion overrides are present in CSS; OS-level reduced-motion emulation was not available in this browser run.
- Corrected the static-file MIME mapping for SVG/other assets in the server source. The already-running `8083` process predates that change, so direct SVG `<img>` loading through that process was not revalidated; visible marks do not depend on that response because their matching official vector paths render from CSS data URIs.

This is evidence for the assistant/dock slice only, not acceptance or a quality score for the whole Landing page. Continue to hold the Landing gate until the remaining page-level visual and interaction review passes.
