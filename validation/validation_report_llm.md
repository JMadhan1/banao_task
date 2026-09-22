# Classifier validation — mode=llm, n=90

Ground truth: the ticket's own `category` field (bot-tagged at intake, agent-corrected at closure — the closest thing to a human judgment call already in the data). Prediction: classifier run on `customer_message` alone, blind to the stored category.

**Overall accuracy: 56.7%**

## Accuracy by true category

| true                |   accuracy |   n |
|:--------------------|-----------:|----:|
| Other               |   0        |  12 |
| Product Enquiry     |   0.2      |   5 |
| Returns & Refunds   |   0.25     |   8 |
| Delivery & Shipping |   0.625    |  16 |
| Audio Quality       |   0.666667 |   6 |
| Charging & Battery  |   0.714286 |   7 |
| Connectivity        |   0.777778 |   9 |
| Account & Login     |   0.8      |   5 |
| Warranty & Repair   |   0.8      |   5 |
| App & Firmware      |   0.8      |   5 |
| Billing & Payments  |   0.833333 |  12 |

## Top confusions

| true                | pred                |   n |
|:--------------------|:--------------------|----:|
| Other               | Returns & Refunds   |   5 |
| Delivery & Shipping | Warranty & Repair   |   4 |
| Returns & Refunds   | Delivery & Shipping |   4 |
| Other               | Product Enquiry     |   2 |
| Product Enquiry     | Billing & Payments  |   2 |
| Account & Login     | Billing & Payments  |   1 |
| App & Firmware      | Connectivity        |   1 |
| Charging & Battery  | App & Firmware      |   1 |
| Charging & Battery  | Warranty & Repair   |   1 |
| Billing & Payments  | App & Firmware      |   1 |
| Audio Quality       | Warranty & Repair   |   1 |
| Audio Quality       | Billing & Payments  |   1 |
| Other               | App & Firmware      |   1 |
| Delivery & Shipping | Returns & Refunds   |   1 |
| Delivery & Shipping | Other               |   1 |
