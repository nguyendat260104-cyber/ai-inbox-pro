# Revenue optimization scoring

Campaign ranking uses observable evidence only:

| Component | Weight | Evidence rule |
|---|---:|---|
| Accessibility | 20 | Approved account plus valid source/affiliate URL and Vietnam availability |
| Demand/hotness evidence | 25 | Visible ratings/sold signals or observed clicks; no invented search volume |
| Purchase ease | 20 | Low-ticket, clear problem-solution, low checkout friction |
| Content fit | 20 | Demonstrable use case, at least five angles, buyer-intent keywords |
| Compliance/measurement | 15 | Policy-safe disclosure, tracking path, payout path and source record |

Hard gates: missing affiliate link is `BLOCKED`; missing commission source is `needs_verification`; no campaign is called “hot” without an evidence record. Scores in `config/product_sources.json` are pre-link hypotheses and cannot authorize publishing.
