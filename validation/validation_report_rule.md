# Classifier validation — mode=rule, n=220

Ground truth: the ticket's own `category` field (bot-tagged at intake, agent-corrected at closure — the closest thing to a human judgment call already in the data). Prediction: classifier run on `customer_message` alone, blind to the stored category.

**Overall accuracy: 40.9%**

## Accuracy by true category

| true                |   accuracy |   n |
|:--------------------|-----------:|----:|
| Product Enquiry     |  0.0909091 |  11 |
| Audio Quality       |  0.266667  |  15 |
| Other               |  0.290323  |  31 |
| Connectivity        |  0.333333  |  21 |
| Returns & Refunds   |  0.363636  |  22 |
| Warranty & Repair   |  0.363636  |  11 |
| Charging & Battery  |  0.5       |  18 |
| Account & Login     |  0.5       |   6 |
| Delivery & Shipping |  0.5       |  40 |
| Billing & Payments  |  0.533333  |  30 |
| App & Firmware      |  0.6       |  15 |

## Top confusions

| true                | pred                |   n |
|:--------------------|:--------------------|----:|
| Delivery & Shipping | Other               |  14 |
| Returns & Refunds   | Delivery & Shipping |  12 |
| Connectivity        | Other               |   8 |
| Billing & Payments  | Other               |   6 |
| Product Enquiry     | Other               |   6 |
| Other               | Delivery & Shipping |   6 |
| Other               | Returns & Refunds   |   5 |
| Audio Quality       | Returns & Refunds   |   4 |
| Audio Quality       | Other               |   4 |
| Other               | Charging & Battery  |   4 |
| App & Firmware      | Returns & Refunds   |   4 |
| Billing & Payments  | Returns & Refunds   |   4 |
| Product Enquiry     | App & Firmware      |   4 |
| Charging & Battery  | Returns & Refunds   |   4 |
| Connectivity        | Returns & Refunds   |   4 |
