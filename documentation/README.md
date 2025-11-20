# AWS Build Review Scripts

Comprehensive toolset for collecting AWS infrastructure data and verifying it against HLDs (High-Level Designs) and detailed design specifications.

## Overview

This toolkit provides:
1. **Data Collection Script** (`aws_build_review.py`) - Collects comprehensive AWS infrastructure configuration
2. **Verification Script** (`aws_build_verification.py`) - Analyzes collected data and generates verification reports

## What Data Gets Collected

### Network Layer
- **VPC Configuration**: CIDR blocks, subnets (public/private), availability zones
- **Routing**: Route tables, Internet Gateways, NAT Gateways
- **Security**: Security Groups (all rules), Network ACLs, VPC Peering
- **DNS**: Route53 hosted zones and record sets

### Compute Resources
- **EC2**: Instance configurations, AMIs, instance types, security groups, IAM profiles
- **Lambda**: Function configurations, runtime, memory, timeout, VPC settings, environment variables
- **ECS**: Cluster configurations, services, task definitions, container settings
- **EKS**: Kubernetes clusters, node groups, versions, VPC configuration

### Databases
- **RDS**: Instance/cluster configurations, engine versions, storage, backup settings, Multi-AZ, encryption
- **ElastiCache**: Redis/Memcached clusters, node types, replication, encryption

### Load Balancing
- **ALB/NLB**: Load balancer configurations, listeners, SSL policies, target groups, health checks

### Storage
- **S3**: Bucket configurations, versioning, encryption, public access blocks, logging, lifecycle policies

### Security & Access
- **IAM**: Roles, policies (managed and inline), assume role policies, users
- **Security Groups**: All ingress/egress rules, overly permissive rules detection

### Monitoring & Logging
- **CloudWatch**: Alarms, metrics, alarm actions
- **CloudWatch Logs**: Log groups, retention policies

## Prerequisites

```bash
# Install Python dependencies
pip install -r requirements.txt

# Configure AWS credentials
aws configure --profile your-profile-name

# Or use environment variables
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=eu-west-2
```

## Usage

### Step 1: Collect AWS Infrastructure Data

```bash
# Basic usage (uses default credentials and region)
python aws_build_review.py

# Specify AWS profile and region
python aws_build_review.py --profile prod-account --region eu-west-2

# Custom output file
python aws_build_review.py --profile prod-account --output client_prod_infrastructure.json
```

**Output**: A comprehensive JSON file containing all AWS infrastructure configuration.

### Step 2: Verify Against Design Specifications

```bash
# Basic verification (analyzes against best practices)
python aws_build_verification.py --collected-data aws_build_review_output.json

# With design specification comparison
python aws_build_verification.py \
  --collected-data aws_build_review_output.json \
  --design-spec client_design_spec.json \
  --output verification_report.json
```

## Verification Checks

The verification script automatically checks for:

### Network Architecture
- ✅ Proper subnet distribution across availability zones
- ✅ Public vs private subnet configuration
- ✅ Internet Gateway presence for public subnets
- ✅ NAT Gateway presence for private subnets
- ✅ Route table associations
- ✅ VPC peering configurations

### Security
- 🔒 Security groups open to 0.0.0.0/0
- 🔒 Overly permissive rules
- 🔒 Database public accessibility
- 🔒 S3 bucket encryption status
- 🔒 S3 public access blocks
- 🔒 IAM role trust policies

### High Availability
- 🌍 Multi-AZ deployments for databases
- 🌍 Load balancer AZ distribution
- 🌍 ECS service distribution
- 🌍 Target health status

### Compliance & Best Practices
- 📝 S3 versioning enabled
- 📝 S3 logging enabled
- 📝 RDS backup retention periods
- 📝 CloudWatch alarms configured
- 📝 Log group retention policies

## Multi-Region Collection

For multi-region environments:

```bash
#!/bin/bash
# collect_all_regions.sh

REGIONS=("eu-west-1" "eu-west-2" "us-east-1")
PROFILE="prod-account"

for region in "${REGIONS[@]}"; do
  echo "Collecting data for region: $region"
  python aws_build_review.py \
    --profile $PROFILE \
    --region $region \
    --output "aws_review_${region}.json"
done
```

## Multi-Account Collection

For multi-account organizations:

```bash
#!/bin/bash
# collect_all_accounts.sh

ACCOUNTS=("prod" "staging" "dev")

for account in "${ACCOUNTS[@]}"; do
  echo "Collecting data for account: $account"
  python aws_build_review.py \
    --profile $account \
    --output "aws_review_${account}.json"
done
```

## Design Specification Format

To enable comparison against design specifications, create a JSON file:

```json
{
  "vpc": {
    "cidr": "10.0.0.0/16",
    "subnets": {
      "public": ["10.0.1.0/24", "10.0.2.0/24"],
      "private": ["10.0.10.0/24", "10.0.11.0/24"]
    },
    "nat_gateways": 2,
    "availability_zones": ["eu-west-2a", "eu-west-2b"]
  },
  "compute": {
    "ec2": [
      {
        "name": "web-server",
        "type": "t3.medium",
        "count": 2
      }
    ],
    "lambda": [
      {
        "name": "api-handler",
        "runtime": "python3.11",
        "memory": 512
      }
    ]
  },
  "databases": {
    "rds": [
      {
        "identifier": "prod-db",
        "engine": "postgres",
        "version": "15.4",
        "instance_class": "db.t3.medium",
        "multi_az": true
      }
    ]
  },
  "security": {
    "allowed_ingress": ["443", "22"],
    "encryption_required": true
  }
}
```

## Report Interpretation

### JSON Output Structure

```json
{
  "AccountId": "123456789012",
  "Region": "eu-west-2",
  "CollectionTimestamp": "2025-11-18T12:00:00",
  "Sections": [
    {
      "title": "VPC Architecture Verification",
      "checks": [...]
    },
    {
      "title": "Security Group Verification",
      "checks": [...]
    }
  ]
}
```

### Key Findings

Look for these severity indicators:
- **HIGH**: Security risks (e.g., 0.0.0.0/0 access, public databases)
- **MEDIUM**: Best practice violations (e.g., no encryption, single AZ)
- **LOW**: Optimization opportunities
- **INFO**: Informational items

## Common Use Cases

### 1. Pre-Deployment Verification

```bash
# Before going live, collect and verify
python aws_build_review.py --profile staging
python aws_build_verification.py --collected-data aws_build_review_output.json
```

### 2. Post-Deployment Audit

```bash
# After deployment, verify against design
python aws_build_verification.py \
  --collected-data prod_infrastructure.json \
  --design-spec approved_design.json
```

### 3. Compliance Audit

Run monthly to ensure ongoing compliance:

```bash
#!/bin/bash
DATE=$(date +%Y-%m-%d)
python aws_build_review.py --output "audit_${DATE}.json"
python aws_build_verification.py --collected-data "audit_${DATE}.json"
```

### 4. Change Detection

Compare infrastructure over time:

```bash
# Collect before changes
python aws_build_review.py --output before_changes.json

# Make changes via Terraform/CloudFormation

# Collect after changes
python aws_build_review.py --output after_changes.json

# Compare (you can use jq or a diff tool)
diff <(jq -S . before_changes.json) <(jq -S . after_changes.json)
```

## IAM Permissions Required

The data collection script needs these IAM permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:Describe*",
        "elasticloadbalancing:Describe*",
        "rds:Describe*",
        "s3:GetBucket*",
        "s3:ListBucket",
        "s3:ListAllMyBuckets",
        "lambda:List*",
        "lambda:Get*",
        "iam:List*",
        "iam:Get*",
        "cloudwatch:Describe*",
        "logs:Describe*",
        "route53:List*",
        "route53:Get*",
        "elasticache:Describe*",
        "ecs:Describe*",
        "ecs:List*",
        "eks:Describe*",
        "eks:List*",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

## Security Considerations

1. **Credentials**: Never commit AWS credentials to version control
2. **Output Files**: The JSON output contains sensitive configuration data - handle appropriately
3. **Access Control**: Store reports in secure locations with appropriate access controls
4. **S3 Access**: The script attempts to read bucket configurations - ensure appropriate permissions

## Troubleshooting

### Error: "Access Denied"
- Check IAM permissions for the role/user
- Verify you're using the correct AWS profile
- Some resources may be in different regions

### Error: "Region not specified"
- Set default region: `aws configure set region eu-west-2`
- Or use `--region` flag explicitly

### Large Output Files
- Output files can be 10-50MB for large environments
- Consider using `jq` for filtering: `jq '.VPC' aws_build_review_output.json`

### Timeouts
- For very large environments (1000+ resources), collection may take 10-15 minutes
- Use `--profile` and `--region` to scope collection

## Extending the Scripts

### Adding New AWS Services

Edit `aws_build_review.py` and add a new method:

```python
def get_my_service_configuration(self) -> Dict[str, Any]:
    """Collect MyService configuration"""
    client = self.session.client('myservice')
    resources = client.list_resources()
    return {'MyService': resources}
```

Then add it to `collect_all_data()`:

```python
collections = [
    # ... existing collections
    ('MyService', self.get_my_service_configuration),
]
```

### Adding Custom Verification Checks

Edit `aws_build_verification.py` and add a new method:

```python
def verify_my_custom_check(self) -> Dict[str, Any]:
    """Custom verification logic"""
    results = {'title': 'My Custom Check', 'checks': []}
    # Your verification logic here
    return results
```

## Integration with CI/CD

### GitLab CI Example

```yaml
aws_build_review:
  stage: verify
  script:
    - pip install -r requirements.txt
    - python aws_build_review.py --profile prod
    - python aws_build_verification.py --collected-data aws_build_review_output.json
  artifacts:
    paths:
      - aws_build_review_output.json
      - verification_report.json
    expire_in: 30 days
```

### GitHub Actions Example

```yaml
name: AWS Build Review
on: [push]
jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: aws-actions/configure-aws-credentials@v1
        with:
          aws-region: eu-west-2
      - run: pip install -r requirements.txt
      - run: python aws_build_review.py
      - run: python aws_build_verification.py --collected-data aws_build_review_output.json
```

## Support

For Djinn Six Limited clients:
- Contact your engagement lead
- Email: support@djinnsix.com (if applicable)

## License

Proprietary - Djinn Six Limited
For client use only under service agreement terms.
