# Classifier validation — mode=rule, n=60

Ground truth: the ticket's own `category` field (bot-tagged at intake, agent-corrected at closure — the closest thing to a human judgment call already in the data). Prediction: classifier run on `customer_message` alone, blind to the stored category.

**Overall accuracy: 43.3%**

## Accuracy by true category

| true                |   accuracy |   n |
|:--------------------|-----------:|----:|
| Account & Login     |   0        |   2 |
| Product Enquiry     |   0.2      |   5 |
| Connectivity        |   0.333333 |   6 |
| Other               |   0.375    |   8 |
| Charging & Battery  |   0.4      |   5 |
| Audio Quality       |   0.4      |   5 |
| Delivery & Shipping |   0.5      |  10 |
| Billing & Payments  |   0.5      |   6 |
| Warranty & Repair   |   0.5      |   4 |
| Returns & Refunds   |   0.5      |   6 |
| App & Firmware      |   1        |   3 |

## Top confusions

| true                | pred                |   n |
|:--------------------|:--------------------|----:|
| Delivery & Shipping | Other               |   5 |
| Connectivity        | Other               |   3 |
| Returns & Refunds   | Delivery & Shipping |   2 |
| Product Enquiry     | App & Firmware      |   2 |
| Billing & Payments  | Other               |   2 |
| Product Enquiry     | Other               |   2 |
| Other               | Returns & Refunds   |   2 |
| Account & Login     | Returns & Refunds   |   2 |
| Other               | Charging & Battery  |   1 |
| Audio Quality       | App & Firmware      |   1 |
| Billing & Payments  | App & Firmware      |   1 |
| Charging & Battery  | Other               |   1 |
| Other               | Delivery & Shipping |   1 |
| Returns & Refunds   | Other               |   1 |
| Warranty & Repair   | App & Firmware      |   1 |
