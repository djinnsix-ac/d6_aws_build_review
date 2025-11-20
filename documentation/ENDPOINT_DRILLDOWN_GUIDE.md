# SageMaker Model Endpoint Drill-Down - Visual Guide

## 🎯 Overview

The enhanced HTML report now provides **comprehensive drill-down** capabilities for SageMaker Model Endpoints. Click any endpoint in the report to reveal detailed configuration, security settings, and operational information.

---

## 📊 What You'll See

### Main Table View (Collapsed)

```
🌐 Model Endpoints
┌────────────────────────────────────────────────────────────────────────┐
│ Endpoint                           │ Severity │ Issues │ Recommendation│
│                                    │          │        │               │
├────────────────────────────────────┼──────────┼────────┼───────────────┤
│ kda-pokerrecommender              │  MEDIUM  │ ⚠️ ME...│ Use customer- │
│ ▼ Click for details               │          │        │ managed KMS...│
├────────────────────────────────────┼──────────┼────────┼───────────────┤
│ ml-fraud-detection-prod           │  INFO    │ ✓ No...│ Endpoint pr...│
│ ▼ Click for details               │          │        │               │
└────────────────────────────────────┴──────────┴────────┴───────────────┘
```

### Expanded View (After Clicking)

```
🌐 Model Endpoints
┌────────────────────────────────────────────────────────────────────────┐
│ kda-pokerrecommender              │  MEDIUM  │ ⚠️ ME...│ Use customer- │
│ ▲ Click to collapse               │          │        │ managed KMS...│
├────────────────────────────────────┴──────────┴────────┴───────────────┤
│                                                                         │
│  📋 ENDPOINT CONFIGURATION                                             │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ Endpoint Name:   kda-pokerrecommender                           │  │
│  │ ARN:             arn:aws:sagemaker:us-east-1:123456789012:      │  │
│  │                  endpoint/kda-pokerrecommender                  │  │
│  │ Status:          ●  InService                                    │  │
│  │ Created:         2025-11-15 10:30:00 UTC                        │  │
│  │ Last Modified:   2025-11-18 14:22:15 UTC                        │  │
│  │ Endpoint Config: poker-recommender-config-v3                    │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  🔐 ENCRYPTION & SECURITY                                              │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ KMS Key:                                                         │  │
│  │   ⚠️  Not configured                                            │  │
│  │                                                                  │  │
│  │ Security Recommendation:                                         │  │
│  │   Use customer-managed KMS keys for data encryption at rest     │  │
│  │                                                                  │  │
│  │   Benefits:                                                      │  │
│  │   • Full control over key rotation                              │  │
│  │   • Audit trail via CloudTrail                                  │  │
│  │   • Compliance with data protection requirements                │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  📊 DATA CAPTURE CONFIGURATION                                         │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ Data Capture Enabled:  No                                        │  │
│  │                                                                  │  │
│  │ Note: Data capture is disabled. If you need model monitoring,   │  │
│  │       consider enabling data capture to an encrypted S3 bucket. │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  🚀 PRODUCTION VARIANTS (ACTIVE)                                       │
│  ┌────────────┬────────────────────┬──────────────┬────────┬────────┐ │
│  │ Variant    │ Model Name         │ Instance     │ Count  │ Weight │ │
│  │ Name       │                    │ Type         │        │        │ │
│  ├────────────┼────────────────────┼──────────────┼────────┼────────┤ │
│  │ AllTraffic │ poker-reco-model-1 │ ml.m5.xlarge │   1    │  1.0   │ │
│  └────────────┴────────────────────┴──────────────┴────────┴────────┘ │
│                                                                         │
│  ⚙️  ENDPOINT CONFIG - PRODUCTION VARIANTS                             │
│                                                                         │
│  ▼ 📦 Variant: AllTraffic                                              │
│    ┌─────────────────────────────────────────────────────────────┐   │
│    │ Model Name:            poker-reco-model-1                    │   │
│    │ Instance Type:         ml.m5.xlarge                          │   │
│    │ Initial Instance Count: 1                                    │   │
│    │ Initial Weight:        1.0                                   │   │
│    │ Container Image:       123456789012.dkr.ecr.us-east-1.      │   │
│    │                        amazonaws.com/sagemaker-xgboost:     │   │
│    │                        1.5-1                                │   │
│    │ Model Data URL:        s3://ml-models/poker-recommender/    │   │
│    │                        model.tar.gz                         │   │
│    └─────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  🏷️ TAGS                                                                │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ Environment:       production                                    │  │
│  │ Owner:             ml-team                                       │  │
│  │ CostCenter:        engineering                                   │  │
│  │ Project:           poker-recommendations                         │  │
│  │ DataClassification: confidential                                 │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🔍 Information Now Available

### 1. Endpoint Configuration
**What It Tells You:**
- Full endpoint ARN for AWS Console access
- Current operational status
- When the endpoint was created and last modified
- Which endpoint configuration is being used

**Why It Matters:**
- Quickly identify stale endpoints (old creation dates)
- Verify endpoint is actually serving traffic (InService status)
- Track configuration changes over time

---

### 2. Encryption & Security
**What It Tells You:**
- Whether customer-managed KMS keys are in use
- Specific security recommendations

**Why It Matters:**
- **CRITICAL for compliance**: Many regulations require customer-managed encryption
- Audit trail: KMS keys provide CloudTrail logs of all encryption/decryption
- Key rotation: You control when and how keys are rotated

**What to Do If Missing:**
```bash
# Update endpoint config to use KMS
aws sagemaker create-endpoint-config \
  --endpoint-config-name poker-reco-config-kms \
  --kms-key-id arn:aws:kms:us-east-1:123456789012:key/abc-123 \
  --production-variants VariantName=AllTraffic,...

# Update endpoint to use new config
aws sagemaker update-endpoint \
  --endpoint-name kda-pokerrecommender \
  --endpoint-config-name poker-reco-config-kms
```

---

### 3. Data Capture Configuration
**What It Tells You:**
- Is data capture enabled? (for model monitoring)
- Where is captured data being sent?
- What percentage of requests are being captured?

**Why It Matters:**
- **Data exposure risk**: If enabled, inference requests/responses go to S3
- **S3 bucket security**: You must verify the destination bucket is properly secured
- **Cost implications**: Data capture can generate significant S3 storage costs
- **Privacy/compliance**: Captured data may contain PII/sensitive information

**Security Checklist When Data Capture is Enabled:**
- ✅ S3 bucket has encryption enabled
- ✅ S3 bucket blocks public access
- ✅ S3 bucket has access logging enabled
- ✅ S3 bucket has lifecycle policies for data retention
- ✅ IAM policies restrict who can access captured data

---

### 4. Production Variants (Active)
**What It Tells You:**
- Which model(s) are actually serving traffic right now
- Instance types and counts
- Traffic distribution weights

**Why It Matters:**
- **Cost optimization**: Identify expensive instance types that could be right-sized
- **Capacity planning**: See if instance counts match expected load
- **A/B testing visibility**: If multiple variants, see traffic split

**Example Interpretation:**
```
Variant Name: AllTraffic
Model: poker-reco-model-1
Instance: ml.m5.xlarge (1 instance)
Weight: 1.0

Translation: 100% of traffic goes to poker-reco-model-1 
running on a single ml.m5.xlarge instance.
```

---

### 5. Endpoint Config - Production Variants
**What It Tells You:**
- Detailed configuration of each variant
- Container image being used
- Where the model artifacts are stored (S3)

**Why It Matters:**
- **Reproducibility**: Know exactly which Docker image and model version is deployed
- **Security**: Verify model artifacts are in secure S3 buckets
- **Troubleshooting**: Quickly identify mismatched configurations

**Example Use Case:**
You notice inference errors. Check:
1. Container image version → Is it the latest?
2. Model data URL → Is the S3 path correct?
3. Instance type → Is it adequate for the model size?

---

### 6. Tags
**What It Tells You:**
- Environment (production, staging, dev)
- Owner/team responsible
- Cost center for billing
- Data classification level
- Project association

**Why It Matters:**
- **Cost allocation**: Accurately attribute costs to teams/projects
- **Compliance**: Verify data classification tags match actual data sensitivity
- **Access control**: Tag-based IAM policies can restrict who manages endpoints
- **Automation**: Tags can trigger automated actions (e.g., backup, monitoring)

**Red Flags to Watch For:**
- Missing "Environment" tag → May deploy to wrong environment
- Missing "DataClassification" → May handle data inappropriately
- Inconsistent "Owner" → Unclear who to contact for issues

---

## 🎯 Practical Scenarios

### Scenario 1: Security Audit
**Task:** Verify all production endpoints use customer-managed KMS keys

**Steps:**
1. Open HTML report
2. Navigate to SageMaker → Model Endpoints
3. Click each endpoint marked "production" in tags
4. Check Encryption & Security section
5. Flag any showing "⚠️ Not configured"

**Time Saved:** Manually checking AWS Console for 10 endpoints: ~15 minutes
With drill-down: ~2 minutes

---

### Scenario 2: Cost Optimization Review
**Task:** Find endpoints using expensive instance types with low utilization

**Steps:**
1. Review Production Variants section for each endpoint
2. Note instance types (e.g., ml.p3.8xlarge vs ml.m5.large)
3. Cross-reference with CloudWatch metrics (if available)
4. Identify candidates for downsizing

**What to Look For:**
- Large instance types (ml.p3, ml.p4, ml.g4) for simple models
- Instance counts > 1 when traffic doesn't justify
- GPU instances (ml.p*) for CPU-only inference

---

### Scenario 3: Data Privacy Compliance
**Task:** Ensure no PII is being captured without proper controls

**Steps:**
1. Click each endpoint
2. Check Data Capture Configuration
3. If enabled, verify:
   - S3 bucket is encrypted
   - Access is restricted
   - Data retention policies exist
4. Check Tags for DataClassification
5. Verify data capture is appropriate for classification level

**Compliance Rule Example:**
```
IF DataClassification = "PII" OR "PHI"
AND Data Capture = Enabled
THEN:
  - S3 bucket MUST use customer-managed KMS
  - S3 bucket MUST have access logging
  - S3 bucket MUST have lifecycle policy (max 90 days)
  - IAM access MUST be restricted to security-cleared roles
```

---

### Scenario 4: Incident Response
**Task:** Endpoint is returning errors; need to investigate configuration

**Steps:**
1. Click affected endpoint
2. Check Status → Is it InService?
3. Check Last Modified → Recent config change?
4. Review Endpoint Config - Production Variants:
   - Is the container image correct?
   - Is the model data URL accessible?
   - Is the instance type adequate?
5. Check Tags → Who is the Owner to contact?

**Information at Your Fingertips:**
- Endpoint ARN for AWS Console access
- Exact container image and version
- Model artifact location
- Configuration history (via timestamps)
- Contact information (via tags)

---

## 🚀 Getting Started

### 1. Generate the Report
```bash
# Collect data
python3 aws_build_review-v2_3_0.py \
  --profile your-profile \
  --region us-east-1 \
  --output aws_data.json

# Verify configuration
python3 aws_build_verification-v2_5_0.py \
  --collected-data aws_data.json \
  --output verification.json

# Generate HTML
python3 generate_html_report-v2_7_0.py \
  --input verification.json \
  --output security_report.html
```

### 2. Open the Report
```bash
# Linux/Mac
open security_report.html

# Windows
start security_report.html

# Or just double-click the file
```

### 3. Navigate to Endpoints
1. Scroll to **🧠 Amazon SageMaker Security** section
2. Find **🌐 Model Endpoints** subsection
3. Click any endpoint row

### 4. Explore the Details
- Read through each subsection
- Note any security warnings
- Check compliance with your organization's standards
- Document findings for remediation

---

## 💡 Pro Tips

### Tip 1: Compare Endpoints
Open the report in a browser and use browser search (Ctrl+F / Cmd+F) to find specific:
- Instance types: Search for "ml.m5" to find all M5 instances
- KMS keys: Search for "Not configured" to find unencrypted endpoints
- Tags: Search for "production" to focus on production endpoints

### Tip 2: Export for Further Analysis
The HTML uses standard table elements. You can:
1. Click an endpoint to expand
2. Right-click → Inspect Element
3. Find the `<table>` with endpoint details
4. Copy HTML and paste into Excel/Sheets for sorting/filtering

### Tip 3: Bookmark Important Sections
The HTML report has section headers with IDs. Create browser bookmarks:
- `security_report.html#sagemaker-section` (future enhancement)
- Save multiple reports with dates: `security_report_2025-11-18.html`

### Tip 4: Share Specific Findings
When reporting issues:
1. Click the endpoint to expand
2. Take a screenshot of the specific subsection
3. Attach to ticket/email with context already visible

---

## 📸 Visual Examples

### Example 1: Compliant Endpoint
```
🌐 Model Endpoints

ml-fraud-detection-prod                    │  INFO    │ ✓ No...│ Endpoint pr...
▼ Click for details

📋 Endpoint Configuration
   Status: ● InService
   
🔐 Encryption & Security  
   KMS Key: arn:aws:kms:us-east-1:123456789012:key/abc-123
   Security Recommendation: ✓ Using customer-managed KMS key

📊 Data Capture Configuration
   Enabled: Yes
   S3 URI: s3://ml-monitoring-encrypted/fraud-detection/
   ⚠️ Verify S3 bucket security:
      ✓ Encryption enabled
      ✓ Public access blocked
      ✓ Access logging enabled
```

### Example 2: Non-Compliant Endpoint
```
🌐 Model Endpoints

legacy-model-endpoint                      │ MEDIUM  │ ⚠️ ME...│ Use customer...
▼ Click for details

🔐 Encryption & Security  
   KMS Key: ⚠️ Not configured
   
   Security Recommendation:
   Use customer-managed KMS keys for data encryption at rest

📊 Data Capture Configuration
   Enabled: Yes
   S3 URI: s3://old-monitoring-bucket/
   
   ⚠️ Data capture is enabled. Verify S3 bucket security:
      • Ensure bucket encryption is enabled
      • Verify bucket policy restricts public access
      • Check lifecycle policies for data retention
      • Confirm access logging is enabled
      
   ⚠️⚠️ CRITICAL: This endpoint captures data but has no KMS encryption!
```

---

## 🎓 Training Resources

### For Security Teams
**Focus areas:**
- Encryption & Security section
- Data Capture Configuration warnings
- Tag compliance (DataClassification)

**Key questions:**
- Are all production endpoints using customer-managed KMS?
- Is data capture properly secured when enabled?
- Do tags match security policies?

### For ML Engineers  
**Focus areas:**
- Production Variants (instance types, counts)
- Container images and model data URLs
- Endpoint status and last modified dates

**Key questions:**
- Are we using appropriate instance types?
- Are model versions correct?
- When was this endpoint last updated?

### For FinOps Teams
**Focus areas:**
- Production Variants (instance types, counts, weights)
- Tags (CostCenter, Environment)
- Endpoint status (paying for unused endpoints?)

**Key questions:**
- Can we right-size any endpoints?
- Are we paying for InService endpoints that aren't used?
- Is cost allocation tagging accurate?

---

## ✅ Checklist: Using the Drill-Down Effectively

Weekly review:
- [ ] Generate fresh HTML report
- [ ] Click through each production endpoint
- [ ] Verify KMS encryption in place
- [ ] Check data capture S3 bucket security
- [ ] Confirm tags are accurate
- [ ] Look for expensive instance types
- [ ] Check for stale endpoints (old Last Modified dates)
- [ ] Document any findings
- [ ] Create remediation tickets

Monthly deep dive:
- [ ] Export endpoint configs for trend analysis
- [ ] Compare instance usage to CloudWatch metrics
- [ ] Review all non-production endpoints (do they need to exist?)
- [ ] Audit tag compliance across all endpoints
- [ ] Calculate total monthly endpoint costs
- [ ] Identify optimization opportunities

---

**Questions?** Check the main CHANGELOG or review the inline documentation in the Python scripts.
