# Revenue Activation

The repository can prepare campaigns while Shopee payout setup is pending. It cannot create an affiliate account, accept tax terms, enter bank/tax data, publish content, or spend on ads.

## Human handoff fields

For each product slot, the user supplies the real `product_id` and affiliate URL copied from the approved Shopee/Lazada portal. Commission and cookie fields remain `needs_verification` until shown by the portal or an official source.

## State model

`needs_user_link` means content and tracking can be prepared, but the campaign cannot be published. `ready_for_human_review` means account, product ID, link, and tracking metadata are present; payout is still separately visible. `ready_to_publish` is never set by automation.

## Tracking convention

Use a stable non-secret ID such as `shopee-home-01-tiktok-organic-v1`. Keep click/order/revenue metrics empty until platform reports them. Never estimate conversions or commission.
