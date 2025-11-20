# IAM Security Analysis - Major Feature Addition

## 🎯 What Changed

Previously: IAM data was collected but only counted (X roles, Y policies)
Now: Full security analysis of IAM permissions and policies

## 📦 Updated Files

### 1. aws_build_verification-v2.3.0.py
✅ Added `_analyze_iam_policy_security()` - Deep policy analysis engine
✅ Complete rewrite of `verify_iam()` - Now outputs security findings in `checks` format
✅ Added `_get_iam_remediation()` - Contextual remediation guidance

### 2. generate_html_report-v2.5.0.py
✅ Updated `generate_iam_section()` - Displays security findings
✅ Backward compatible with old format
✅ New table layout with severity badges and detailed issues

---

## 🔐 IAM Security Checks Implemented

### CRITICAL Violations

| Check | Description | Example |
|-------|-------------|---------|
| **Full Admin Access** | Action: * with Resource: * | Unrestricted access to everything |
| **AdministratorAccess Policy** | AWS managed admin policy attached | Full AWS account access |
| **Wildcard Trust Policy** | Trust policy allows * (any AWS account) | Anyone can assume role |

### HIGH Violations

| Check | Description | Example |
|-------|-------------|---------|
| **Wildcard Permissions** | Wildcard action with Resource: * | `s3:*` on `Resource: *` |
| **Sensitive Actions Unrestricted** | IAM/KMS/Secrets actions on all resources | `iam:CreateUser` on `*` |
| **Privilege Escalation Risks** | Actions that can elevate privileges | `iam:AttachUserPolicy`, `iam:PassRole` |

### MEDIUM Violations

| Check | Description | Example |
|-------|-------------|---------|
| **PassRole Without Conditions** | Can pass any role to any service | No `iam:PassedToService` condition |
| **Full Service Access** | Service wildcard on all resources | `lambda:*` on `Resource: *` |
| **Root Account Trust** | Trust policy allows root account | `:root` in Principal |
| **IAM Users Exist** | Human users instead of SSO | Should use AWS IAM Identity Center |

### LOW Violations

| Check | Description | Example |
|-------|-------------|---------|
| **Broad Service Permissions** | Service wildcards | `ec2:*`, `rds:*` on all resources |

---

## 🔍 What's Analyzed

### 1. Inline Policies
- Every statement in inline policy documents
- Action and Resource combinations
- Presence/absence of Condition keys

### 2. Attached Managed Policies
- Checks for AWS managed admin policies
- AdministratorAccess
- PowerUserAccess

### 3. Trust Policies (AssumeRolePolicyDocument)
- Wildcard principals (*)
- Root account access
- Cross-account trust configurations

### 4. Specific Action Patterns
**Privilege Escalation Actions:**
- iam:CreatePolicyVersion
- iam:SetDefaultPolicyVersion
- iam:PassRole
- iam:CreateAccessKey
- iam:AttachUserPolicy / AttachRolePolicy
- iam:PutUserPolicy / PutRolePolicy
- iam:UpdateAssumeRolePolicy

**Sensitive Actions:**
- IAM user/role creation and modification
- KMS Decrypt and CreateGrant
- Secrets Manager GetSecretValue
- S3 object operations
- Lambda function updates
- EC2 instance launches

---

## 📊 HTML Report Output

### IAM Security Analysis Section

**Alert Banner:**
- 🚨 Red banner for CRITICAL issues
- ⚠️ Orange banner for HIGH issues
- ⚠️ Yellow banner for MEDIUM issues
- ✓ Green info for compliant

**Roles Table:**
| Role | Severity | Attached | Inline | Security Issues | Recommendation |
|------|----------|----------|--------|-----------------|----------------|
| AdminRole | 🚨 CRITICAL | 1 | 0 | AdministratorAccess policy attached | Remove AdministratorAccess... |
| LambdaRole | ⚠️ HIGH | 0 | 2 | Action: * with Resource: * | Apply least privilege... |

**IAM Users Alert:**
```
⚠️ MEDIUM: 3 IAM User(s) Found
⚠️ MEDIUM: 3 IAM user(s) found - consider using AWS SSO/Identity Center instead
Recommendation: Migrate to AWS IAM Identity Center (SSO) for human users
```

---

## 🎯 Example Findings

### Example 1: CRITICAL - Full Admin
```json
{
  "Resource": "Role: DevelopmentRole",
  "Severity": "CRITICAL",
  "Issues": [
    "🚨 CRITICAL: Full admin access - Action: * with Resource: * (inline: AllowAll)"
  ],
  "Recommendation": "🔒 CRITICAL: Remove overly permissive policies immediately | 🔒 Apply least privilege principle"
}
```

### Example 2: HIGH - Privilege Escalation
```json
{
  "Resource": "Role: DeploymentRole",
  "Severity": "HIGH",
  "Issues": [
    "⚠️ HIGH: Privilege escalation risk - iam:AttachUserPolicy, iam:PutRolePolicy without restrictions (inline: DeployPolicy)"
  ],
  "Recommendation": "🔒 HIGH: Reduce permission scope to specific resources | 🔒 Remove privilege escalation paths"
}
```

### Example 3: MEDIUM - PassRole
```json
{
  "Resource": "Role: ServiceRole",
  "Severity": "MEDIUM",
  "Issues": [
    "⚠️ MEDIUM: iam:PassRole without conditions - can pass any role to any service (inline: ServicePolicy)"
  ],
  "Recommendation": "🔒 Add conditions to iam:PassRole (e.g., iam:PassedToService)"
}
```

---

## 🚀 How to Use

### Step 1: Run Data Collection
```bash
python3 aws_build_review-v2.2.0.py \
  --profile my-profile \
  --region us-east-1 \
  --output aws_data.json
```

### Step 2: Run Security Verification (NEW VERSION)
```bash
python3 aws_build_verification-v2.3.0.py \
  --collected-data aws_data.json \
  --output verification.json
```

### Step 3: Generate HTML Report (NEW VERSION)
```bash
python3 generate_html_report-v2.5.0.py \
  --input verification.json \
  --output security_report.html
```

### Step 4: Review IAM Section
Open `security_report.html` and scroll to the **🔐 IAM Security Analysis** section.

---

## ⚠️ What This DOESN'T Check

This analysis does NOT:
- Fetch full policy documents for AWS managed policies (only checks for known risky ones like AdministratorAccess)
- Analyze customer managed policies that aren't attached to roles
- Check IAM user policies (only checks that users exist)
- Validate Condition keys are correctly formatted
- Check for service control policies (SCPs)
- Analyze resource-based policies (S3 bucket policies, Lambda policies, etc.)

This DOES:
- Analyze all inline policies completely
- Check trust policies (AssumeRolePolicy)
- Identify attached AWS managed admin policies
- Detect privilege escalation paths
- Flag overly permissive wildcards

---

## 📋 Version Summary

| Script | Old Version | New Version | Change |
|--------|-------------|-------------|--------|
| aws_build_review | v2.2.0 | v2.2.0 | No change (still collects same data) |
| aws_build_verification | v2.2.0 | **v2.3.0** | Major: Added IAM security analysis |
| generate_html_report | v2.4.1 | **v2.5.0** | Major: New IAM security display |

---

## 🎉 Impact

**Before:**
```
IAM Configuration
─────────────────
Role: AdminRole | Attached: 1 | Inline: 0
Role: LambdaRole | Attached: 0 | Inline: 2
Role: ServiceRole | Attached: 2 | Inline: 1
```

**After:**
```
🚨 Found 1 CRITICAL IAM security issue(s) requiring immediate attention!

IAM Roles - Security Analysis
─────────────────────────────────────────────────────────
Role: AdminRole | 🚨 CRITICAL | Issues:
  • 🚨 CRITICAL: AdministratorAccess policy attached
  Recommendation: 🔒 CRITICAL: Remove overly permissive policies immediately

Role: LambdaRole | ⚠️ HIGH | Issues:
  • ⚠️ HIGH: Wildcard permissions - Action with wildcard on Resource: *
  • ⚠️ HIGH: Sensitive action 'lambda:UpdateFunctionCode' with Resource: *
  Recommendation: 🔒 HIGH: Reduce permission scope to specific resources

Role: ServiceRole | ⚠️ MEDIUM | Issues:
  • ⚠️ MEDIUM: iam:PassRole without conditions
  Recommendation: 🔒 Add conditions to iam:PassRole (e.g., iam:PassedToService)
```

---

## ✅ Testing

To test the new IAM analysis:
1. Ensure you have IAM roles with inline policies in your AWS account
2. Run the complete pipeline
3. Check the HTML report for the IAM Security Analysis section
4. Look for severity badges and specific security issues
5. Review recommendations for each finding

---

## 🔧 Troubleshooting

**"IAM section shows old format (just counts)"**
- You're using old verification script (v2.2.0 or earlier)
- Use **aws_build_verification-v2.3.0.py**

**"No IAM issues shown but I know I have admin roles"**
- Check if policies are attached (managed) vs inline
- Inline policies are fully analyzed
- Managed policies only checked if they're AWS admin policies

**"Want to check customer managed policies"**
- These are collected but not currently analyzed
- Future enhancement possible if needed
