# IAM Permissions for CIS Benchmark Security Audit

## Required Permissions for aws_build_review-v2.3.0.py

### CloudTrail (CIS 3.1-3.4)
```json
{
    "Effect": "Allow",
    "Action": [
        "cloudtrail:DescribeTrails",
        "cloudtrail:GetTrailStatus",
        "cloudtrail:GetEventSelectors"
    ],
    "Resource": "*"
}
```

### VPC Flow Logs (CIS 3.7)
```json
{
    "Effect": "Allow",
    "Action": [
        "ec2:DescribeFlowLogs",
        "ec2:DescribeVpcs"
    ],
    "Resource": "*"
}
```

### IAM Password Policy (CIS 1.5-1.11)
```json
{
    "Effect": "Allow",
    "Action": [
        "iam:GetAccountPasswordPolicy"
    ],
    "Resource": "*"
}
```

### IAM Credential Report (CIS 1.4, 1.12-1.15)
```json
{
    "Effect": "Allow",
    "Action": [
        "iam:GenerateCredentialReport",
        "iam:GetCredentialReport",
        "iam:GetAccountSummary",
        "iam:ListVirtualMFADevices"
    ],
    "Resource": "*"
}
```

### AWS Config (CIS 3.5)
```json
{
    "Effect": "Allow",
    "Action": [
        "config:DescribeConfigurationRecorders",
        "config:DescribeConfigurationRecorderStatus"
    ],
    "Resource": "*"
}
```

### IAM Access Analyzer
```json
{
    "Effect": "Allow",
    "Action": [
        "access-analyzer:ListAnalyzers"
    ],
    "Resource": "*"
}
```

## Complete Combined Policy

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "CISBenchmarkAuditReadOnly",
            "Effect": "Allow",
            "Action": [
                "cloudtrail:DescribeTrails",
                "cloudtrail:GetTrailStatus",
                "cloudtrail:GetEventSelectors",
                "ec2:DescribeFlowLogs",
                "ec2:DescribeVpcs",
                "iam:GetAccountPasswordPolicy",
                "iam:GenerateCredentialReport",
                "iam:GetCredentialReport",
                "iam:GetAccountSummary",
                "iam:ListVirtualMFADevices",
                "config:DescribeConfigurationRecorders",
                "config:DescribeConfigurationRecorderStatus",
                "access-analyzer:ListAnalyzers"
            ],
            "Resource": "*"
        }
    ]
}
```

## What These Permissions Enable

### CRITICAL Checks (CIS Level 1):
1. ✅ Root account access keys exist (1.4)
2. ✅ Root account MFA status (1.14)
3. ✅ CloudTrail enabled and configured (3.1-3.4)
4. ✅ VPC Flow Logs enabled (3.7)

### HIGH Priority Checks:
1. ✅ IAM password policy compliance (1.5-1.11)
2. ✅ IAM user MFA enabled (1.15)
3. ✅ AWS Config enabled (3.5)

### MEDIUM Priority Checks:
1. ✅ Unused credentials (1.12)
2. ✅ Multiple active access keys (1.13)
3. ✅ Access key rotation (1.14)
4. ✅ IAM Access Analyzer enabled

## Permission Justification

All permissions are **read-only** and required for security compliance auditing:

- **CloudTrail**: Essential for detecting if audit logging is enabled
- **VPC Flow Logs**: Required to verify network traffic logging
- **IAM Password Policy**: Checks if weak passwords are prevented
- **Credential Report**: Contains user credential age/usage data
- **AWS Config**: Verifies configuration change tracking
- **Access Analyzer**: Checks for unintended external access

**Note**: All actions only support `Resource: "*"` - this is AWS's design for account-level read operations.
