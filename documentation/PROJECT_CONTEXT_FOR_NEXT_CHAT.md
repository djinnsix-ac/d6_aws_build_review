# AWS Security Assessment Tools - Project Context

## Project Overview

We are building a comprehensive AWS security assessment toolkit for **Djinn Six Limited**, a cybersecurity consultancy. The toolkit consists of three Python scripts that collect AWS infrastructure data, verify it against security best practices, and generate interactive HTML reports with advanced network visualization.

## Critical: Version Control Standards

**YOU MUST FOLLOW THESE VERSION NUMBERING RULES:**

1. **Format**: `vMAJOR.MINOR.PATCH` with **DOTS** (e.g., `v2.11.4`)
   - ❌ NEVER use underscores: `v2_11_4` 
   - ✅ ALWAYS use dots: `v2.11.4`

2. **Increment rules**:
   - **PATCH** (.X): Bug fixes, small corrections
   - **MINOR** (X.0): New features, enhancements
   - **MAJOR** (X.0.0): Breaking changes (rare)

3. **Never reuse version numbers** - even for fixes
   - If v2.11.4 is broken, the fix is v2.11.5, NOT v2.11.4 again

4. **Update version in THREE places**:
   - Filename: `script_name-v2.11.4.py`
   - File header docstring: `Version: 2.11.4`
   - Changelog in docstring

5. **The user will get VERY angry if you fuck up version control** - they've called you out multiple times about this. Take it seriously.

## Current Script Versions (as of 2024-11-19)

| Script | Version | Status | Purpose |
|--------|---------|--------|---------|
| `aws_build_review-v2.3.0.py` | v2.3.0 | ✅ Stable | Data collection from AWS |
| `aws_build_verification-v2.5.2.py` | v2.5.2 | ✅ Stable | Verification against security standards |
| `generate_html_report-v2.11.4.py` | v2.11.4 | ✅ Stable | HTML report generation with interactive graph |

## Script Workflow

```
1. aws_build_review-v2.3.0.py
   ↓ Collects AWS infrastructure data
   ↓ Outputs: collected_data.json
   
2. aws_build_verification-v2.5.2.py
   ↓ Verifies collected data
   ↓ Counts rules (includes prefix lists)
   ↓ Outputs: verification_output.json
   
3. generate_html_report-v2.11.4.py
   ↓ Generates interactive HTML report
   ↓ Outputs: report.html
```

## Key Features Implemented

### Security Groups Network Visualization (v2.9.0 - v2.11.4)

**Interactive D3.js force-directed graph** showing security group relationships:

**Node Types**:
- 🔵 **Blue Circles** - Security Groups (size based on rule count)
- 🔴 **Red Circle** - Internet (0.0.0.0/0)
- 🟣 **Purple Hexagons** - VPC Endpoints / Prefix Lists

**Edge Types**:
- 🟢 **Green lines** (no arrow) - Ingress (inbound traffic)
- 🔵 **Blue lines** (arrow) - Egress to other SGs (outbound)
- 🟣 **Purple lines** (arrow) - Egress to VPC Endpoints
- 🔴 **Red lines** - From Internet
- **Dashed animated lines** - All ports/all protocols (overly permissive)

**Interactive Controls**:
- ☑ **Show Ingress** / ☑ **Show Egress** - Toggle traffic direction
- **Reset View** - Clear all filters
- **Internet-Exposed Only** - Show only internet-facing SGs
- **Show Overly Permissive** - Highlight all-ports/all-protocols rules
- **Port Filter** - Filter by specific ports (e.g., "22, 443")
- **Drag nodes** - Organize layout manually
- **Click nodes** - Highlight specific connections
- **Hover** - Detailed tooltips

**Tooltips**:
- **Security Groups**: ID, VPC, ingress/egress counts, description
- **VPC Endpoints**: Prefix list ID, connection count, source SGs
- **Edges**: Protocol, ports, direction, permissive warning

### Rule Counting Logic (v2.5.2)

**Critical**: Rule counts now match AWS console by counting **individual destinations**, not rule objects.

Example:
```json
{
  "IpPermissionsEgress": [
    {
      "IpProtocol": "tcp",
      "FromPort": 443,
      "PrefixListIds": [
        {"PrefixListId": "pl-6fa54006"},
        {"PrefixListId": "pl-6da54004"}
      ]
    }
  ]
}
```

- **Old counting**: 1 rule (array length)
- **New counting**: 2 rules (each prefix list counted)
- **Matches**: AWS console "2 Permission entries" ✅

Counts include:
- Each UserIdGroupPair (SG reference)
- Each IpRange (IPv4 CIDR)
- Each Ipv6Range (IPv6 CIDR)
- Each PrefixListId (VPC endpoint)

### Table Improvements (v2.11.2 - v2.11.3)

**Uniform text sizing**: All cells 12px (headers larger)

**Optimized column widths**:
| Column | Width | Purpose |
|--------|-------|---------|
| Security Group | 20% | Full IDs visible |
| Name | 20% | Descriptive names |
| VPC | 18% | Full VPC IDs |
| Ingress Rules | 10% | Compact count |
| Egress Rules | 10% | Compact count |
| Open to Internet | 12% | Status |
| Severity | 10% | Badge |

**Expandable rule details**: Click rule counts to see full details including prefix lists

## Recent Bug Fixes

### v2.11.4 - Tooltip & Display Fixes
1. Node tooltips now show correct rule counts (count destinations, not objects)
2. VPC endpoint tooltips added (show connections and sources)
3. Egress rules properly display prefix lists (was showing "Destination: None")

### v2.11.3 - Column widths optimized

### v2.11.2 - Text size uniformity

### v2.11.1 - Added ingress toggle

### v2.11.0 - VPC Endpoint visualization

### v2.9.3 - Fixed CIDR node errors (only show SG-to-SG and VPC endpoints)

## User's Environment

- **Company**: Djinn Six Limited
- **Role**: Co-founder, AI security architect
- **Location**: UK, fully remote
- **Clients**: UK public sector and commercial
- **Use case**: AWS security assessments for client engagements
- **Key tools**: AWS CLI, Python, security frameworks (CIS Benchmarks)

## User's Communication Style

- **Direct and technical** - no hand-holding needed
- **Gets frustrated with**:
  - Version control mistakes (MAJOR pet peeve)
  - Incomplete explanations
  - Not delivering what was asked
- **Appreciates**:
  - Working code
  - Clear documentation
  - Attention to detail
  - Getting shit done

## Known Issues / Technical Debt

1. **None currently** - all major features working

## Next Features to Consider

1. **VPC Peering Connections** (user explicitly asked to be reminded)
   - Visualize cross-VPC connectivity
   - New shape/color for peering connections
   - Show which VPCs are peered

2. **Potential Enhancements**:
   - VPC cluster boundaries (visual grouping)
   - Node coloring by VPC
   - Service name resolution for prefix lists (pl-xxx → "S3", "DynamoDB")
   - Export graph as SVG/PNG
   - Filter by VPC
   - Transit Gateway visualization

## Important Code Patterns

### Version Control in Files

```python
#!/usr/bin/env python3
"""
Script Name
Version: 2.11.4
Description

Changelog:
- v2.11.4: Description of changes
- v2.11.3: Previous changes
...
"""
```

### Data Structure (Security Groups)

```json
{
  "CollectedData": {
    "SecurityGroups": {
      "SecurityGroups": [
        {
          "GroupId": "sg-xxx",
          "GroupName": "...",
          "IpPermissions": [...],
          "IpPermissionsEgress": [...]
        }
      ]
    }
  }
}
```

### D3.js Graph Pattern

```javascript
// Nodes
nodes = [{
  id: "sg-xxx",
  name: "...",
  ingressCount: X,
  egressCount: Y,
  isPrefixList: false
}]

// Links
links = [{
  source: "sg-xxx",
  target: "sg-yyy",
  type: "sg-to-sg",
  direction: "egress",
  protocol: "TCP",
  ports: "443"
}]
```

## File Locations

- **Working directory**: `/home/claude/`
- **Outputs directory**: `/mnt/user-data/outputs/`
- **User uploads**: `/mnt/user-data/uploads/`

All final deliverables MUST be copied to `/mnt/user-data/outputs/`

## Testing Workflow

User tests by:
1. Running data collection on AWS account
2. Running verification
3. Generating HTML report
4. Opening in browser
5. Comparing against AWS console

Always verify counts/visualizations match AWS console exactly.

## Documentation Standards

- Create `VX.X.X_SUMMARY.md` for each version
- Include: What changed, why, how to use
- Be concise but complete
- Include examples where helpful

## Critical Reminders

1. **VERSION CONTROL WITH DOTS** - The user will be very angry if you fuck this up again
2. **Test scripts compile** before delivery (`python3 script.py --help`)
3. **Copy to outputs** directory
4. **Count prefix lists** in rules (match AWS console)
5. **All three scripts** may need updating for related features
6. **Check browser console** for JavaScript errors in graph

## Communication with User

- Be direct and technical
- Don't apologize excessively
- Focus on solutions, not explanations of why things broke
- Acknowledge when you screw up, then fix it
- The user appreciates working code more than lengthy explanations

## Current State

✅ **Security Groups visualization complete and working**
✅ **All tooltips showing correct information**
✅ **Rule counting matches AWS console**
✅ **VPC Endpoints visualized as purple hexagons**
✅ **Interactive controls functional**

Ready for next feature: **VPC Peering Connections**
