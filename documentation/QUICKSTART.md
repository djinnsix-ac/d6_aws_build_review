# AWS Build Review - Quick Start Guide

## 🚀 Getting Started in 5 Minutes

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Configure AWS Access
```bash
# Option A: Use AWS CLI configuration
aws configure --profile client-account

# Option B: Use environment variables
export AWS_ACCESS_KEY_ID="your-key"
export AWS_SECRET_ACCESS_KEY="your-secret"
export AWS_DEFAULT_REGION="eu-west-2"
```

### Step 3: Run Collection
```bash
# Simple collection
python3 aws_build_review.py

# Or use the wrapper script
chmod +x run_build_review.sh
./run_build_review.sh --profile client-account --region eu-west-2
```

### Step 4: Generate Verification Report
```bash
python3 aws_build_verification.py --collected-data aws_build_review_output.json
```

### Step 5: Generate HTML Report (Optional)
```bash
python3 generate_html_report.py --input verification_report.json --output report.html
```

## 📋 Common Client Scenarios

### Scenario 1: New Client Assessment
```bash
# Collect infrastructure data
python3 aws_build_review.py --profile new-client --output new_client_infra.json

# Generate verification report
python3 aws_build_verification.py \
  --collected-data new_client_infra.json \
  --output new_client_verification.json

# Create readable HTML report
python3 generate_html_report.py \
  --input new_client_verification.json \
  --output new_client_report.html
```

### Scenario 2: Verify Against HLD
```bash
# 1. Update design_spec_template.json with client's HLD specifications
# 2. Run collection and verification
python3 aws_build_review.py --profile client
python3 aws_build_verification.py \
  --collected-data aws_build_review_output.json \
  --design-spec design_spec_template.json
```

### Scenario 3: Multi-Region Review
```bash
# Using the wrapper script
./run_build_review.sh --profile client --multi-region
```

### Scenario 4: Pre-Production Sign-Off
```bash
# Before production deployment
python3 aws_build_review.py --profile staging --output staging_review.json
python3 aws_build_verification.py --collected-data staging_review.json

# Review security findings
cat verification_report.json | jq '.Sections[] | select(.title | contains("Security"))'
```

## 🔍 What Gets Checked

### Critical Security Checks
- ✅ Security groups open to 0.0.0.0/0
- ✅ RDS databases publicly accessible
- ✅ S3 buckets without encryption
- ✅ S3 buckets without public access blocks
- ✅ Missing VPC Flow Logs
- ✅ IAM overly permissive policies

### Architecture Validation
- ✅ Multi-AZ deployments
- ✅ Proper subnet distribution
- ✅ NAT Gateway availability
- ✅ Load balancer configuration
- ✅ High availability setup

### Compliance Checks
- ✅ Backup retention policies
- ✅ Encryption at rest
- ✅ Logging enabled
- ✅ Monitoring configured
- ✅ Resource tagging

## 📊 Understanding the Output

### Collection Output (JSON)
Contains complete AWS infrastructure configuration:
- All VPC networking components
- Security group rules
- Compute resources (EC2, Lambda, ECS, EKS)
- Databases (RDS, ElastiCache)
- Storage (S3) configurations
- IAM roles and policies
- Monitoring setup

### Verification Report (JSON)
Structured analysis with:
- Security findings
- Architecture compliance
- Best practice violations
- Resource inventory

### HTML Report
Visual report with:
- Color-coded severity indicators
- Sortable tables
- Executive summary
- Detailed findings

## ⚙️ Customization

### Add Custom Checks
Edit `aws_build_verification.py` and add:
```python
def verify_custom_requirement(self) -> Dict[str, Any]:
    results = {'title': 'Custom Check', 'checks': []}
    # Your logic here
    return results
```

### Modify Design Specifications
Edit `design_spec_template.json` to match client requirements:
```json
{
  "vpc": {
    "cidr": "10.0.0.0/16",
    "nat_gateways": 2
  }
}
```

## 🛠️ Troubleshooting

### "Access Denied" Errors
- Verify IAM permissions (see README.md for required permissions)
- Check AWS profile configuration
- Ensure credentials are valid

### Missing Resources
- Some resources may be in different regions
- Use `--region` flag or multi-region mode
- Check if resources exist in the account

### Large Files
- For large environments, output can be 50MB+
- Use `jq` to filter: `jq '.EC2' aws_build_review_output.json`
- Consider regional scoping

## 📝 Deliverables for Client

Typical engagement deliverables:
1. **Raw Infrastructure Data** - JSON file of complete configuration
2. **Verification Report** - JSON with findings and compliance status
3. **HTML Report** - Formatted report for stakeholders
4. **Executive Summary** - Key findings and recommendations (manual)
5. **Remediation Plan** - Based on findings (manual)

## 🔒 Security & Data Handling

**Important:**
- Output files contain sensitive configuration data
- Store securely and encrypt at rest
- Use appropriate access controls
- Clean up temporary files after delivery
- Follow Djinn Six data handling procedures

## 📞 Support

For Djinn Six team members:
- Check internal documentation for detailed procedures
- Contact lead architect for complex scenarios
- Follow client engagement protocols

## 💡 Pro Tips

1. **Run collections during low-traffic periods** to avoid impacting monitoring
2. **Keep design specs in version control** for change tracking
3. **Automate regular reviews** for ongoing clients
4. **Compare reports over time** to track infrastructure drift
5. **Filter findings by severity** for prioritization

## 📅 Recommended Schedule

### Initial Assessment
- Full infrastructure collection
- Comprehensive verification
- HTML report generation
- Client presentation

### Ongoing Monitoring (Monthly)
- Quick collection and verification
- Delta comparison with previous month
- Flag new issues
- Track remediation progress

### Pre-Deployment Reviews
- Collection of target environment
- Verification against approved design
- Sign-off documentation

---

**Version:** 1.0  
**Updated:** 2025-11-18  
**Maintained by:** Djinn Six Limited
