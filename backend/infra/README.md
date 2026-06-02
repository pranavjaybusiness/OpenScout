# OpenScout feedback alarm (user clicked **No**)

The API publishes **`FeedbackMatchNo`** (namespace **`OpenScout`**) on every successful `POST /feedback` with `user_feedback: "no"`. Lambda must have **`cloudwatch:PutMetricData`** on role `openscout_backend`.

## Deploy alarm + email (recommended)

1. **CloudFormation** → **Create stack** → **Upload a template file** → `feedback-no-alarm.yaml`
2. Region: **us-east-2**
3. Parameter **AlertEmail**: your email
4. Create stack → open the SNS email → **Confirm subscription**
5. Click **No** once in the extension → within ~2 minutes you should get **ALARM** email

Alarm settings: **Sum** ≥ **1** over **60s**, **1** evaluation period. Each No click in a given minute increments the count.

## Console-only (if you prefer not to use the template)

**CloudWatch** → **Alarms** → **Create alarm** → **Select metric** → namespace **OpenScout** → **FeedbackMatchNo**

| Setting | Value |
|--------|--------|
| Statistic | **Sum** (not Average) |
| Period | 1 minute |
| Threshold | **≥ 1** |
| Datapoints to alarm | 1 of 1 |
| Missing data | **notBreaching** |
| Notification | SNS topic (create topic + email subscription first) |

Common mistakes: wrong namespace, wrong metric, statistic Average with sparse data, threshold > 1, no confirmed SNS subscription.

## Investigate each **No**

### DynamoDB (full row: product, Gemini snapshot, eBay pick)

**DynamoDB** → **OpenScoutHistory** → **Explore table items** → filter attribute **`user_feedback`** = **`no`**

Each row has **`scan_id`**, **`product_url`**, **`product_data`**, **`gemini_verification`**, **`analyzed_at`**.

### CloudWatch Logs (quick lookup by scan)

**Log groups** → `/aws/lambda/OpenScoutApi` → **Logs Insights**:

```sql
fields @timestamp, scan_id, product_url, user_feedback
| filter event = "feedback_received" and user_feedback = "no"
| sort @timestamp desc
| limit 50
```

Use **`scan_id`** to open the matching DynamoDB item.
