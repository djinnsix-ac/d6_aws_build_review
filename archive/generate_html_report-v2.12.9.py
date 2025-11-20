#!/usr/bin/env python3
"""
AWS Build Review HTML Report Generator
Version: 2.12.9
Converts JSON verification reports readable HTML format

Changelog:
- v2.12.9: Standardized font sizes across all tables - body text 12px, headers default browser size
- v2.12.8: Added Network ACLs section with clickable subnet associations, uniform text sizing, optimized column widths
- v2.12.7: Fixed h4 heading font sizes - VPC name, Endpoints, and Peering now all same size (18px)
- v2.12.6: Route Tables improvements - uniform text size, better column widths, ✅/❌ emojis, clickable subnets with details
- v2.12.4: Fixed arrow rendering - use HTML entities (&#9658;/&#9660;) instead of Unicode characters
- v2.12.3: Fixed VPC heading hierarchy and collapsible sections - VPC name at h4 level, Configuration/Subnet/Route Tables at h5 collapsible, VPC Endpoints/Peering also collapsible
- v2.12.2: Enhanced VPC section - collapsible Subnet Distribution & Route Tables, clickable IGW/RT details, show route table associations
- v2.12.1: Enhanced VPC Architecture formatting - prominent VPC headings, better labels, hierarchical subnet view, IGW/NAT links
- v2.12.0: FEATURE - Added VPC Endpoints and VPC Peering sections with drill-down details
- v2.11.7: BUGFIX - Show compliance issues for all affected rules; sort rules by severity (CRITICAL→HIGH→MEDIUM→LOW→COMPLIANT)
- v2.11.6: BUGFIX - Rule numbering continues across multiple IpPermissions (Rule 1, 2, 3 not 1, 1, 2); detect 0-65535 as "All Ports"; add IP Version and Type fields
- v2.11.5: BUGFIX - Rule display shows each destination as separate numbered rule; VPC endpoint tooltips improved with service names and bulleted sources
- v2.11.4: BUGFIX - Node tooltips use correct rule counts, add details for VPC endpoint tooltips
- v2.11.3: Adjusted table column widths for better readability, count prefix lists in egress rules
- v2.11.2: BUGFIX - Uniform text size in security groups table (all cells same size)
- v2.11.1: Added ingress toggle to match egress toggle
- v2.11.0: Added VPC Endpoint/Prefix List visualization (purple hexagons) and updated rule counting
- v2.10.1: BUGFIX - Smaller egress arrows, blue color for distinction, better positioning
- v2.10.0: Enhanced graph - VPC grouping, node sizing, egress flows, all-ports highlighting, port filter
- v2.9.3: BUGFIX - Fixed "node not found" error for CIDR ranges (only visualize SG-to-SG and Internet)
- v2.9.2: Added debug logging to network graph for troubleshooting
- v2.9.1: BUGFIX - Fixed security group data extraction path (nested SecurityGroups.SecurityGroups)
- v2.9.0: Added D3.js interactive network graph for security group connections (ports/protocols)
- v2.8.1: Made all major sections collapsible via JavaScript - reduces scrolling
- v2.7.0: Added detailed drill-down for SageMaker Model Endpoints with collapsible sections  
- v2.6.0: Added CIS AWS Foundations Benchmark section with color-coded severity
- v2.5.0: Added Bedrock and SageMaker sections with detailed security checks
"""

import json
import argparse
from pathlib import Path
from datetime import datetime


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AWS Build Review Report - {account_id}</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        header {{
            border-bottom: 3px solid #2c5aa0;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        
        h1 {{
            color: #2c5aa0;
            font-size: 32px;
            margin-bottom: 10px;
        }}
        
        .meta {{
            display: flex;
            gap: 30px;
            color: #666;
            font-size: 14px;
        }}
        
        .meta-item {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .section {{
            margin: 30px 0;
            padding: 0;
            background: #f9f9f9;
            border-radius: 6px;
            border-left: 4px solid #2c5aa0;
            overflow: hidden;
            max-width: 100%;
        }}
        
        .section h2 {{
            color: #2c5aa0;
            font-size: 24px;
            margin: 0;
            padding: 20px;
            cursor: pointer;
            user-select: none;
            background: #f9f9f9;
        }}
        
        .section h2:hover {{
            background: #e8eef5;
        }}
        
        .section h2::before {{
            content: '▼ ';
            display: inline-block;
            transition: transform 0.3s;
            font-size: 18px;
        }}
        
        .section.collapsed h2::before {{
            transform: rotate(-90deg);
        }}
        
        .section.collapsed .section-body {{
            display: none;
        }}
        
        .section-body {{
            padding: 0 20px 20px 20px;
            overflow-x: auto;
        }}
        
        h3 {{
            color: #555;
            font-size: 18px;
            margin: 15px 0 10px 0;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
            background: white;
            border-radius: 6px;
            overflow: hidden;
            table-layout: fixed;
            font-size: 12px;  /* Standardize all table body text to 12px */
        }}
        
        table td {{
            word-wrap: break-word;
            overflow-wrap: break-word;
        }}
        
        th {{
            background: #2c5aa0;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            font-size: 14px;  /* Standardize all table headers to 14px */
        }}
        
        td {{
            padding: 10px 12px;
            border-bottom: 1px solid #eee;
        }}
        
        tr:last-child td {{
            border-bottom: none;
        }}
        
        tr:hover {{
            background: #f5f5f5;
        }}
        
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
        }}
        
        .badge-high {{
            background: #fee;
            color: #c00;
        }}
        
        .badge-medium {{
            background: #fff3cd;
            color: #856404;
        }}
        
        .badge-low {{
            background: #d1ecf1;
            color: #0c5460;
        }}
        
        .badge-info {{
            background: #e7f3ff;
            color: #004085;
        }}
        
        .badge-success {{
            background: #d4edda;
            color: #155724;
        }}
        
        .badge-warning {{
            background: #fff3cd;
            color: #856404;
        }}
        
        .badge-danger {{
            background: #f8d7da;
            color: #721c24;
        }}
        
        .stat-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 6px;
            border-left: 4px solid #2c5aa0;
        }}
        
        .stat-value {{
            font-size: 32px;
            font-weight: bold;
            color: #2c5aa0;
        }}
        
        .stat-label {{
            color: #666;
            font-size: 14px;
            margin-top: 5px;
        }}
        
        .alert {{
            padding: 15px;
            border-radius: 6px;
            margin: 15px 0;
        }}
        
        .alert-warning {{
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            color: #856404;
        }}
        
        .alert-danger {{
            background: #f8d7da;
            border-left: 4px solid #dc3545;
            color: #721c24;
        }}
        
        .code {{
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
        }}
        
        footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            text-align: center;
            color: #666;
            font-size: 14px;
        }}
        
        .expandable {{
            cursor: pointer;
            user-select: none;
        }}
        
        .expandable:before {{
            content: '▶ ';
            display: inline-block;
            transition: transform 0.2s;
        }}
        
        .expandable.expanded:before {{
            transform: rotate(90deg);
        }}
        
        .expandable-content {{
            display: none;
            margin-left: 20px;
            margin-top: 10px;
        }}
        
        .expandable-content.visible {{
            display: block;
        }}
        
        .remediation-btn {{
            background: #2c5aa0;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            margin-top: 4px;
        }}
        
        .remediation-btn:hover {{
            background: #1e3d6b;
        }}
        
        .remediation-row {{
            background: #f9f9f9 !important;
        }}
        
        .remediation-row td {{
            padding: 0 !important;
        }}
        
        .remediation-details {{
            padding: 20px;
            background: white;
            border-radius: 6px;
            margin: 10px;
            max-width: 100%;
            overflow: hidden;
        }}
        
        .remediation-details h4 {{
            color: #2c5aa0;
            margin-top: 20px;
            margin-bottom: 10px;
            font-size: 18px;
            word-wrap: break-word;
        }}
        
        .remediation-details h5 {{
            color: #555;
            margin-top: 15px;
            margin-bottom: 8px;
            font-size: 16px;
            word-wrap: break-word;
        }}
        
        .remediation-details h6 {{
            color: #666;
            margin-top: 10px;
            margin-bottom: 5px;
            font-size: 14px;
            word-wrap: break-word;
        }}
        
        .remediation-details p {{
            word-wrap: break-word;
            overflow-wrap: break-word;
            margin: 8px 0;
        }}
        
        .remediation-details ul {{
            margin: 10px 0;
            padding-left: 20px;
        }}
        
        .remediation-details li {{
            margin: 5px 0;
            word-wrap: break-word;
        }}
        
        .remediation-step {{
            background: #f5f5f5;
            padding: 15px;
            border-radius: 6px;
            margin: 15px 0;
            border-left: 4px solid #2c5aa0;
            max-width: 100%;
            overflow: hidden;
        }}
        
        .code-block {{
            background: #2d2d2d;
            color: #f8f8f2;
            padding: 12px;
            border-radius: 4px;
            overflow-x: auto;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            line-height: 1.4;
            margin: 8px 0;
            white-space: pre-wrap;
            word-wrap: break-word;
            max-width: 100%;
        }}
        
        .priority-info {{
            background: #fff3cd;
            padding: 12px;
            border-radius: 4px;
            margin: 10px 0;
            border-left: 4px solid #ffc107;
            word-wrap: break-word;
        }}
        
        .alert-info {{
            background: #d1ecf1;
            border-left: 4px solid #0c5460;
            color: #0c5460;
            word-wrap: break-word;
        }}
        
        .tag-expand-link {{
            color: #2c5aa0;
            text-decoration: none;
            font-weight: 600;
            cursor: pointer;
        }}
        
        .tag-expand-link:hover {{
            text-decoration: underline;
        }}
        
        .tags-expanded {{
            margin-top: 8px;
            padding: 8px;
            background: #f0f8ff;
            border-radius: 4px;
            border-left: 3px solid #2c5aa0;
        }}
        
        /* Compact table styling for better tag space */
        .s3-table {{
            table-layout: fixed;
        }}
        
        .s3-table th:nth-child(1), .s3-table td:nth-child(1) {{ width: 15%; }} /* Bucket Name */
        .s3-table th:nth-child(2), .s3-table td:nth-child(2) {{ width: 8%; }}  /* Region */
        .s3-table th:nth-child(3) {{ width: 25%; }} /* Tags header - normal size */
        .s3-table td:nth-child(3) {{ width: 25%; font-size: 11px; }} /* Tags cell - smaller */
        .s3-table th:nth-child(4), .s3-table td:nth-child(4) {{ width: 8%; }}  /* Versioning */
        .s3-table th:nth-child(5), .s3-table td:nth-child(5) {{ width: 8%; }}  /* Encryption */
        .s3-table th:nth-child(6), .s3-table td:nth-child(6) {{ width: 10%; }} /* Public Block */
        .s3-table th:nth-child(7), .s3-table td:nth-child(7) {{ width: 7%; }}  /* Logging */
        .s3-table th:nth-child(8), .s3-table td:nth-child(8) {{ width: 9%; }}  /* Security Score */
        .s3-table th:nth-child(9), .s3-table td:nth-child(9) {{ width: 10%; }} /* Action */
        
        /* Security Groups table - uniform text size for all cells */
        .sg-table td {{
            font-size: 12px;
            padding: 8px;
        }}
        
        /* Security Groups table - column widths for better readability */
        .sg-table th:nth-child(1), .sg-table td:nth-child(1) {{ width: 20%; }} /* Security Group ID */
        .sg-table th:nth-child(2), .sg-table td:nth-child(2) {{ width: 20%; }} /* Name */
        .sg-table th:nth-child(3), .sg-table td:nth-child(3) {{ width: 18%; }} /* VPC */
        .sg-table th:nth-child(4), .sg-table td:nth-child(4) {{ width: 10%; }} /* Ingress Rules */
        .sg-table th:nth-child(5), .sg-table td:nth-child(5) {{ width: 10%; }} /* Egress Rules */
        .sg-table th:nth-child(6), .sg-table td:nth-child(6) {{ width: 12%; }} /* Open to Internet */
        .sg-table th:nth-child(7), .sg-table td:nth-child(7) {{ width: 10%; }} /* Severity */
        
        .compact-cell {{
            font-size: 12px;
            padding: 8px;
        }}
        
        .s3-table .badge {{
            font-size: 10px;
            padding: 3px 8px;
        }}
        
        .s3-table .remediation-btn {{
            font-size: 11px;
            padding: 5px 10px;
        }}
        
        /* Security Group Rules styling */
        .rule-count-link {{
            color: #2c5aa0;
            text-decoration: none;
            font-weight: 600;
            cursor: pointer;
        }}
        
        .rule-count-link:hover {{
            text-decoration: underline;
        }}
        
        .rules-expanded-row {{
            background: #f9f9f9 !important;
        }}
        
        .rules-expanded-row td {{
            padding: 0 !important;
        }}
        
        .rules-details {{
            padding: 20px;
            background: white;
            margin: 10px;
            border-radius: 6px;
        }}
        
        .rules-details h4 {{
            color: #2c5aa0;
            margin-bottom: 15px;
        }}
        
        /* Security Group Network Graph */
        #sg-network-graph {{
            width: 100%;
            height: 600px;
            border: 2px solid #ddd;
            border-radius: 6px;
            background: #fafafa;
            margin: 20px 0;
            position: relative;
        }}
        
        .sg-node {{
            cursor: pointer;
        }}
        
        .sg-node circle {{
            stroke: #fff;
            stroke-width: 2px;
            transition: all 0.3s;
        }}
        
        .sg-node:hover circle {{
            stroke-width: 4px;
        }}
        
        .sg-node text {{
            font-size: 11px;
            pointer-events: none;
            text-anchor: middle;
        }}
        
        .sg-link {{
            stroke-opacity: 0.6;
            transition: all 0.3s;
        }}
        
        .sg-link.permissive {{
            stroke-width: 4px !important;
            stroke-dasharray: 5,5;
            animation: dash 20s linear infinite;
        }}
        
        @keyframes dash {{
            to {{
                stroke-dashoffset: -100;
            }}
        }}
        
        .sg-link-label {{
            font-size: 9px;
            fill: #666;
            pointer-events: none;
        }}
        
        .vpc-cluster {{
            fill: none;
            stroke: #999;
            stroke-width: 1px;
            stroke-dasharray: 5,5;
            opacity: 0.3;
        }}
        
        .vpc-label {{
            font-size: 12px;
            font-weight: bold;
            fill: #666;
        }}
        
        .sg-node.faded circle {{
            opacity: 0.2;
        }}
        
        .sg-node.faded text {{
            opacity: 0.2;
        }}
        
        .sg-link.faded {{
            stroke-opacity: 0.1;
        }}
        
        .sg-tooltip {{
            position: absolute;
            padding: 10px;
            background: rgba(0, 0, 0, 0.9);
            color: white;
            border-radius: 4px;
            pointer-events: none;
            font-size: 12px;
            z-index: 1000;
            max-width: 300px;
        }}
        
        .graph-controls {{
            margin: 15px 0;
            padding: 15px;
            background: #e8eef5;
            border-radius: 6px;
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            align-items: center;
        }}
        
        .graph-controls button {{
            padding: 8px 16px;
            background: #2c5aa0;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }}
        
        .graph-controls button:hover {{
            background: #1e3d6b;
        }}
        
        .graph-legend {{
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
        }}
        
        .legend-color {{
            width: 20px;
            height: 20px;
            border-radius: 50%;
            border: 2px solid #fff;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>AWS Build Review Report</h1>
            <div class="meta">
                <div class="meta-item">
                    <strong>Account:</strong> <span class="code">{account_id}</span>
                </div>
                <div class="meta-item">
                    <strong>Region:</strong> <span class="code">{region}</span>
                </div>
                <div class="meta-item">
                    <strong>Generated:</strong> {timestamp}
                </div>
            </div>
        </header>
        
        {content}
        
        <footer>
            <p>Generated by Djinn Six Limited AWS Build Review Tools</p>
            <p>Report Date: {report_date}</p>
        </footer>
    </div>
    
    <script>
        // Make sections collapsible by wrapping their content and making h2 clickable
        document.addEventListener('DOMContentLoaded', function() {{
            document.querySelectorAll('.section').forEach(section => {{
                // Find the h2
                const h2 = section.querySelector('h2');
                if (!h2) return;
                
                // Get all siblings after h2
                const siblings = [];
                let next = h2.nextElementSibling;
                while (next) {{
                    siblings.push(next);
                    next = next.nextElementSibling;
                }}
                
                // Create wrapper div
                const wrapper = document.createElement('div');
                wrapper.className = 'section-body';
                
                // Move siblings into wrapper
                siblings.forEach(sibling => {{
                    wrapper.appendChild(sibling);
                }});
                
                // Add wrapper after h2
                h2.parentNode.appendChild(wrapper);
                
                // Make h2 clickable to toggle collapsed class
                h2.addEventListener('click', function() {{
                    section.classList.toggle('collapsed');
                    
                    // Initialize security group graph when section is expanded
                    if (!section.classList.contains('collapsed') && 
                        h2.textContent.includes('Security Groups') && 
                        typeof initSecurityGroupGraph === 'function') {{
                        setTimeout(initSecurityGroupGraph, 100);
                    }}
                }});
                
                // Start collapsed
                section.classList.add('collapsed');
            }});
        }});
        
        document.querySelectorAll('.expandable').forEach(el => {{
            el.addEventListener('click', function() {{
                this.classList.toggle('expanded');
                const content = this.nextElementSibling;
                if (content && content.classList.contains('expandable-content')) {{
                    content.classList.toggle('visible');
                }}
            }});
        }});
        
        function toggleRemediation(id) {{
            const row = document.getElementById(id);
            if (row) {{
                if (row.style.display === 'none') {{
                    row.style.display = 'table-row';
                }} else {{
                    row.style.display = 'none';
                }}
            }}
        }}
        
        function toggleTags(id) {{
            const tagsDiv = document.getElementById(id);
            const clickedLink = event.target;
            if (tagsDiv) {{
                if (tagsDiv.style.display === 'none') {{
                    // Expanding - show the div
                    tagsDiv.style.display = 'block';
                }} else {{
                    // Collapsing - hide the div
                    tagsDiv.style.display = 'none';
                }}
            }}
        }}
        
        function toggleRules(id) {{
            const rulesRow = document.getElementById(id);
            if (rulesRow) {{
                if (rulesRow.style.display === 'none') {{
                    rulesRow.style.display = 'table-row';
                }} else {{
                    rulesRow.style.display = 'none';
                }}
            }}
        }}
        
        function toggleSection(id) {{
            const section = document.getElementById(id);
            const icon = document.getElementById(id + '-icon');
            if (section) {{
                if (section.style.display === 'none') {{
                    section.style.display = 'block';
                    if (icon) icon.innerHTML = '&#9660;';  // Down arrow
                }} else {{
                    section.style.display = 'none';
                    if (icon) icon.innerHTML = '&#9658;';  // Right arrow
                }}
            }}
        }}
    </script>
</body>
</html>
"""


def generate_vpc_section(vpc_data, collected_data=None):
    """Generate HTML for VPC architecture section including VPC Endpoints and Peering"""
    if not vpc_data or 'checks' not in vpc_data:
        return ""
    
    html = '<div class="section">\n'
    html += '<h2>VPC Architecture</h2>\n'
    
    # Get raw VPC data for endpoints and peering
    raw_vpcs = []
    if collected_data:
        raw_vpcs = collected_data.get('VPC', {}).get('VPCs', [])
    
    # Group checks by VPC
    vpc_checks = {}
    for check in vpc_data.get('checks', []):
        vpc_id = check.get('VPC')
        if vpc_id:
            if vpc_id not in vpc_checks:
                vpc_checks[vpc_id] = []
            vpc_checks[vpc_id].append(check)
    
    # Display each VPC
    for vpc_id, checks in vpc_checks.items():
        # Find raw VPC data for this VPC
        raw_vpc = next((v for v in raw_vpcs if v.get('VpcId') == vpc_id), None)
        
        # Get VPC name from tags
        vpc_name = 'Unnamed VPC'
        if raw_vpc and raw_vpc.get('Tags'):
            name_tag = next((tag for tag in raw_vpc['Tags'] if tag.get('Key') == 'Name'), None)
            if name_tag:
                vpc_name = name_tag.get('Value', 'Unnamed VPC')
        
        # VPC heading at h4 level (same as VPC Endpoints/Peering)
        html += f'''
        <h4 style="margin-top: 30px; color: #667eea; font-size: 18px; font-weight: 600; border-bottom: 3px solid #667eea; padding-bottom: 8px;">
            VPC: {vpc_name}
            <span style="color: #666; font-size: 14px; font-weight: normal; margin-left: 10px;">({vpc_id})</span>
        </h4>
        '''
        
        # Process checks to extract information
        igw_info = None
        nat_info = None
        subnet_info = None
        vpc_config = None
        route_tables = []
        
        for check in checks:
            check_name = check.get('Check', 'Unknown')
            if check_name == 'Internet Gateway':
                igw_info = check
            elif check_name == 'NAT Gateways':
                nat_info = check
            elif check_name == 'Subnet Distribution':
                subnet_info = check
            elif check_name == 'VPC Configuration':
                vpc_config = check
            elif 'RouteTable' in check:
                route_tables.append(check)
        
        # Configuration section (collapsible h5)
        config_section_id = f"config-{vpc_id}"
        html += f'''<h5 style="margin-top: 20px; color: #2c5aa0; font-size: 15px; cursor: pointer; padding: 8px 0;" 
            onclick="toggleSection('{config_section_id}')">
            <span id="{config_section_id}-icon" style="display: inline-block; width: 20px;">&#9658;</span>
            Configuration
        </h5>\n'''
        
        html += f'<div id="{config_section_id}" style="display: none;">\n'
        html += '<table>\n<thead><tr><th style="width: 30%;">Setting</th><th>Value</th></tr></thead>\n<tbody>\n'
        
        # VPC Configuration
        if vpc_config:
            cidr = vpc_config.get('CIDRBlock', 'N/A')
            is_default = vpc_config.get('IsDefault', False)
            dhcp = vpc_config.get('DHCPOptions', 'N/A')
            
            html += f'<tr><td><strong>CIDR Block</strong></td><td><span class="code">{cidr}</span></td></tr>\n'
            html += f'<tr><td><strong>Default VPC</strong></td><td>{"Yes" if is_default else "No"}</td></tr>\n'
            html += f'<tr><td><strong>DHCP Options Set</strong></td><td><span class="code">{dhcp}</span></td></tr>\n'
        
        # Internet Gateway
        if igw_info:
            has_igw = igw_info.get('Status') == 'Present'
            igw_count = igw_info.get('Value', 0)
            
            if has_igw and raw_vpc:
                igws = raw_vpc.get('InternetGateways', [])
                if igws:
                    # Show first IGW with clickable link
                    igw = igws[0]
                    igw_id = igw.get('InternetGatewayId', '')
                    igw_link = f'<a href="#" onclick="toggleRules(\'igw-details-{vpc_id}\'); return false;" style="color: #2563eb; text-decoration: underline; cursor: pointer;">{igw_id}</a>'
                    html += f'<tr><td><strong>Internet Gateway</strong></td><td>Yes (<span class="code">{igw_link}</span>)</td></tr>\n'
                    
                    # Add expandable row for IGW details
                    html += f'<tr id="igw-details-{vpc_id}" style="display:none;"><td colspan="2">{generate_igw_details(igw)}</td></tr>\n'
                else:
                    html += f'<tr><td><strong>Internet Gateway</strong></td><td>Yes</td></tr>\n'
            else:
                html += f'<tr><td><strong>Internet Gateway</strong></td><td>No</td></tr>\n'
        
        # NAT Gateways
        if nat_info:
            has_nat = nat_info.get('Status') == 'Present'
            nat_count = nat_info.get('Value', 0)
            
            if has_nat and raw_vpc:
                nat_gws = raw_vpc.get('NatGateways', [])
                active_nats = [ng for ng in nat_gws if ng.get('State') == 'available']
                if active_nats:
                    nat_ids = ', '.join([f'<span class="code">{nat.get("NatGatewayId", "")}</span>' for nat in active_nats])
                    html += f'<tr><td><strong>NAT Gateways</strong></td><td>Yes - {len(active_nats)} deployed ({nat_ids})</td></tr>\n'
                else:
                    html += f'<tr><td><strong>NAT Gateways</strong></td><td>Yes - {nat_count} deployed</td></tr>\n'
            else:
                html += f'<tr><td><strong>NAT Gateways</strong></td><td>None deployed</td></tr>\n'
        
        html += '</tbody></table>\n'
        html += '</div>\n'  # Close Configuration collapsible section
        
        # Subnet Distribution - h5 collapsible (starts collapsed)
        if subnet_info:
            subnet_id = f"subnets-{vpc_id}"
            html += f'''<h5 style="margin-top: 20px; color: #2c5aa0; font-size: 15px; cursor: pointer; padding: 8px 0;" 
                onclick="toggleSection('{subnet_id}')">
                <span id="{subnet_id}-icon" style="display: inline-block; width: 20px;">&#9658;</span>
                Subnet Distribution
            </h5>\n'''
            
            public_count = subnet_info.get('PublicSubnets', 0)
            private_count = subnet_info.get('PrivateSubnets', 0)
            az_count = subnet_info.get('AZs', 0)
            distribution = subnet_info.get('Distribution', {})
            
            html += f'<div id="{subnet_id}" style="display: none; padding: 15px; background: #f8f9fa; border-left: 4px solid #2c5aa0; border-radius: 4px; margin: 10px 0;">\n'
            html += f'<p style="margin: 5px 0;"><strong>Public Subnets:</strong> {public_count}</p>\n'
            html += f'<p style="margin: 5px 0;"><strong>Private Subnets:</strong> {private_count}</p>\n'
            html += f'<p style="margin: 5px 0;"><strong>Availability Zones:</strong> {az_count}</p>\n'
            
            if distribution:
                html += '<p style="margin: 15px 0 5px 0;"><strong>Distribution:</strong></p>\n'
                html += '<ul style="margin: 5px 0; padding-left: 20px;">\n'
                
                # Sort AZs alphabetically
                for az in sorted(distribution.keys()):
                    az_data = distribution[az]
                    pub = az_data.get('public', 0)
                    priv = az_data.get('private', 0)
                    html += f'<li><strong>{az}:</strong> {pub} public, {priv} private</li>\n'
                
                html += '</ul>\n'
            
            html += '</div>\n'
        
        # Route Tables summary (h5 collapsible, starts collapsed)
        if route_tables and raw_vpc:
            rt_section_id = f"route-tables-{vpc_id}"
            html += f'''<h5 style="margin-top: 20px; color: #2c5aa0; font-size: 15px; cursor: pointer; padding: 8px 0;" 
                onclick="toggleSection('{rt_section_id}')">
                <span id="{rt_section_id}-icon" style="display: inline-block; width: 20px;">&#9658;</span>
                Route Tables
            </h5>\n'''
            
            html += f'<div id="{rt_section_id}" style="display: none;">\n'
            html += '<table>\n'
            html += '<thead><tr>'
            html += '<th style="width: 25%;">Route Table ID</th>'
            html += '<th style="width: 8%;">Routes</th>'
            html += '<th style="width: 12%;">IGW Route</th>'
            html += '<th style="width: 12%;">NAT Route</th>'
            html += '<th style="width: 10%;">Associations</th>'
            html += '<th style="width: 33%;">Associated With</th>'
            html += '</tr></thead>\n'
            html += '<tbody>\n'
            
            # Get raw route tables from collected data
            raw_route_tables = raw_vpc.get('RouteTables', [])
            
            # Get all subnets for clickable links
            raw_subnets = raw_vpc.get('Subnets', [])
            
            for idx, rt in enumerate(route_tables):
                rt_id = rt.get('RouteTable', 'N/A')
                routes = rt.get('Routes', 0)
                has_igw = rt.get('HasIGWRoute', False)
                has_nat = rt.get('HasNATRoute', False)
                assocs = rt.get('Associations', 0)
                
                # Find the full route table data
                full_rt = next((r for r in raw_route_tables if r.get('RouteTableId') == rt_id), None)
                
                # Get association details with clickable subnets
                assoc_details = "None"
                if full_rt and full_rt.get('Associations'):
                    associations = full_rt['Associations']
                    assoc_list = []
                    for assoc_idx, assoc in enumerate(associations):
                        if assoc.get('Main'):
                            assoc_list.append("Main")
                        elif assoc.get('SubnetId'):
                            subnet_id = assoc['SubnetId']
                            # Find full subnet data
                            full_subnet = next((s for s in raw_subnets if s.get('SubnetId') == subnet_id), None)
                            if full_subnet:
                                # Make subnet clickable
                                subnet_link = f'<a href="#" onclick="toggleRules(\'subnet-details-{vpc_id}-{idx}-{assoc_idx}\'); return false;" style="color: #059669; text-decoration: underline; cursor: pointer;">{subnet_id}</a>'
                                assoc_list.append(f"Subnet: {subnet_link}")
                                # Store subnet for details row
                                assoc.__setitem__('_full_subnet', full_subnet)
                                assoc.__setitem__('_detail_id', f'subnet-details-{vpc_id}-{idx}-{assoc_idx}')
                            else:
                                assoc_list.append(f"Subnet: {subnet_id}")
                        elif assoc.get('GatewayId'):
                            assoc_list.append(f"Gateway: {assoc['GatewayId']}")
                    assoc_details = "<br>".join(assoc_list) if assoc_list else "None"
                
                # Make route table ID clickable
                rt_link = f'<a href="#" onclick="toggleRules(\'rt-details-{vpc_id}-{idx}\'); return false;" style="color: #2563eb; text-decoration: underline; cursor: pointer;">{rt_id}</a>'
                
                # Use emojis for IGW/NAT routes
                igw_display = "✅ Yes" if has_igw else "❌ No"
                nat_display = "✅ Yes" if has_nat else "❌ No"
                
                html += f'''<tr>
                    <td><span class="code">{rt_link}</span></td>
                    <td>{routes}</td>
                    <td>{igw_display}</td>
                    <td>{nat_display}</td>
                    <td>{assocs}</td>
                    <td>{assoc_details}</td>
                </tr>\n'''
                
                # Add expandable row for route table details
                if full_rt:
                    html += f'''<tr id="rt-details-{vpc_id}-{idx}" style="display:none;">
                        <td colspan="6">{generate_route_table_details(full_rt)}</td>
                    </tr>\n'''
                
                # Add expandable rows for subnet details
                if full_rt and full_rt.get('Associations'):
                    for assoc in full_rt['Associations']:
                        if '_full_subnet' in assoc and '_detail_id' in assoc:
                            detail_id = assoc['_detail_id']
                            full_subnet = assoc['_full_subnet']
                            html += f'''<tr id="{detail_id}" style="display:none;">
                                <td colspan="6">{generate_subnet_details(full_subnet)}</td>
                            </tr>\n'''
            
            html += '</tbody></table>\n'
            html += '</div>\n'
        
        # VPC Endpoints Section (h4 collapsible)
        if raw_vpc:
            vpc_endpoints = raw_vpc.get('VpcEndpoints', [])
            if vpc_endpoints:
                endpoints_section_id = f"vpc-endpoints-{vpc_id}"
                html += f'''<h4 style="margin-top: 20px; color: #667eea; font-size: 18px; font-weight: 600; cursor: pointer; padding: 8px 0; border-bottom: 3px solid #667eea;" 
                    onclick="toggleSection('{endpoints_section_id}')">
                    <span id="{endpoints_section_id}-icon" style="display: inline-block; width: 20px;">&#9658;</span>
                    VPC Endpoints ({len(vpc_endpoints)})
                </h4>\n'''
                
                html += f'<div id="{endpoints_section_id}" style="display: none;">\n'
                html += '<table>\n'
                html += '<thead><tr><th>Endpoint ID</th><th>Service Name</th><th>Type</th><th>State</th><th>Details</th></tr></thead>\n'
                html += '<tbody>\n'
                
                for idx, endpoint in enumerate(vpc_endpoints):
                    endpoint_id = endpoint.get('VpcEndpointId', 'N/A')
                    service_name = endpoint.get('ServiceName', 'N/A')
                    endpoint_type = endpoint.get('VpcEndpointType', 'N/A')
                    state = endpoint.get('State', 'N/A')
                    
                    # Make service name more readable
                    display_service = service_name.replace('com.amazonaws.', '').replace(f'.{endpoint.get("VpcRegion", "")}', '')
                    if not display_service:
                        display_service = service_name
                    
                    state_class = 'badge-success' if state == 'available' else 'badge-warning'
                    
                    details_link = f'<a href="#" class="rule-count-link" onclick="toggleRules(\'vpc-endpoint-{vpc_id}-{idx}\'); return false;">View Details</a>'
                    
                    html += f'''<tr>
                        <td><span class="code">{endpoint_id}</span></td>
                        <td>{display_service}</td>
                        <td>{endpoint_type}</td>
                        <td><span class="badge {state_class}">{state}</span></td>
                        <td>{details_link}</td>
                    </tr>\n'''
                    
                    # Expandable details row
                    html += f'''<tr id="vpc-endpoint-{vpc_id}-{idx}" class="rules-expanded-row" style="display:none;">
                        <td colspan="5">
                            <div class="rules-details">
                                {generate_vpc_endpoint_details(endpoint)}
                            </div>
                        </td>
                    </tr>\n'''
                
                html += '</tbody></table>\n'
                html += '</div>\n'  # Close VPC Endpoints collapsible section
        
        # VPC Peering Connections Section (h4 collapsible)
        if raw_vpc:
            peering_connections = raw_vpc.get('VpcPeeringConnections', [])
            if peering_connections:
                peering_section_id = f"vpc-peering-{vpc_id}"
                html += f'''<h4 style="margin-top: 20px; color: #667eea; font-size: 18px; font-weight: 600; cursor: pointer; padding: 8px 0; border-bottom: 3px solid #667eea;" 
                    onclick="toggleSection('{peering_section_id}')">
                    <span id="{peering_section_id}-icon" style="display: inline-block; width: 20px;">&#9658;</span>
                    VPC Peering Connections ({len(peering_connections)})
                </h4>\n'''
                
                html += f'<div id="{peering_section_id}" style="display: none;">\n'
                html += '<table>\n'
                html += '<thead><tr><th>Peering ID</th><th>Requester VPC</th><th>Accepter VPC</th><th>Status</th><th>Details</th></tr></thead>\n'
                html += '<tbody>\n'
                
                for idx, peering in enumerate(peering_connections):
                    peering_id = peering.get('VpcPeeringConnectionId', 'N/A')
                    
                    requester_info = peering.get('RequesterVpcInfo', {})
                    accepter_info = peering.get('AccepterVpcInfo', {})
                    
                    requester_vpc = requester_info.get('VpcId', 'N/A')
                    requester_cidr = requester_info.get('CidrBlock', 'N/A')
                    requester_owner = requester_info.get('OwnerId', 'N/A')
                    
                    accepter_vpc = accepter_info.get('VpcId', 'N/A')
                    accepter_cidr = accepter_info.get('CidrBlock', 'N/A')
                    accepter_owner = accepter_info.get('OwnerId', 'N/A')
                    
                    status_info = peering.get('Status', {})
                    status = status_info.get('Code', 'N/A')
                    
                    status_class = 'badge-success' if status == 'active' else \
                                 'badge-warning' if status == 'pending-acceptance' else \
                                 'badge-danger'
                    
                    details_link = f'<a href="#" class="rule-count-link" onclick="toggleRules(\'vpc-peering-{vpc_id}-{idx}\'); return false;">View Details</a>'
                    
                    html += f'''<tr>
                        <td><span class="code">{peering_id}</span></td>
                        <td><span class="code">{requester_vpc}</span><br><small>{requester_cidr}</small></td>
                        <td><span class="code">{accepter_vpc}</span><br><small>{accepter_cidr}</small></td>
                        <td><span class="badge {status_class}">{status}</span></td>
                        <td>{details_link}</td>
                    </tr>\n'''
                    
                    # Expandable details row
                    html += f'''<tr id="vpc-peering-{vpc_id}-{idx}" class="rules-expanded-row" style="display:none;">
                        <td colspan="5">
                            <div class="rules-details">
                                {generate_vpc_peering_details(peering)}
                            </div>
                        </td>
                    </tr>\n'''
                
                html += '</tbody></table>\n'
                html += '</div>\n'  # Close VPC Peering collapsible section
        
        # Network ACLs Section (h4 collapsible)
        if raw_vpc:
            network_acls = raw_vpc.get('NetworkACLs', [])
            if network_acls:
                nacl_section_id = f"network-acls-{vpc_id}"
                html += f'''<h4 style="margin-top: 20px; color: #667eea; font-size: 18px; font-weight: 600; cursor: pointer; padding: 8px 0; border-bottom: 3px solid #667eea;" 
                    onclick="toggleSection('{nacl_section_id}')">
                    <span id="{nacl_section_id}-icon" style="display: inline-block; width: 20px;">&#9658;</span>
                    Network ACLs ({len(network_acls)})
                </h4>\n'''
                
                html += f'<div id="{nacl_section_id}" style="display: none;">\n'
                html += '<table>\n'
                html += '<thead><tr>'
                html += '<th style="width: 25%;">NACL ID</th>'
                html += '<th style="width: 10%;">Default</th>'
                html += '<th style="width: 12%;">Inbound Rules</th>'
                html += '<th style="width: 12%;">Outbound Rules</th>'
                html += '<th style="width: 10%;">Associations</th>'
                html += '<th style="width: 31%;">Associated Subnets</th>'
                html += '</tr></thead>\n'
                html += '<tbody>\n'
                
                # Get all subnets for clickable links
                raw_subnets = raw_vpc.get('Subnets', [])
                
                for idx, nacl in enumerate(network_acls):
                    nacl_id = nacl.get('NetworkAclId', 'N/A')
                    is_default = nacl.get('IsDefault', False)
                    
                    # Count rules
                    entries = nacl.get('Entries', [])
                    inbound_count = len([e for e in entries if not e.get('Egress', False)])
                    outbound_count = len([e for e in entries if e.get('Egress', False)])
                    
                    # Get associations
                    associations = nacl.get('Associations', [])
                    assoc_count = len(associations)
                    
                    # Build clickable subnet list
                    subnet_list = []
                    for assoc_idx, assoc in enumerate(associations):
                        subnet_id = assoc.get('SubnetId', '')
                        if subnet_id:
                            # Find full subnet data
                            full_subnet = next((s for s in raw_subnets if s.get('SubnetId') == subnet_id), None)
                            if full_subnet:
                                # Make subnet clickable
                                subnet_link = f'<a href="#" onclick="toggleRules(\'nacl-subnet-{vpc_id}-{idx}-{assoc_idx}\'); return false;" style="color: #059669; text-decoration: underline; cursor: pointer;">{subnet_id}</a>'
                                subnet_list.append(subnet_link)
                                # Store for details row
                                assoc['_full_subnet'] = full_subnet
                                assoc['_detail_id'] = f'nacl-subnet-{vpc_id}-{idx}-{assoc_idx}'
                            else:
                                subnet_list.append(subnet_id)
                    
                    subnet_display = "<br>".join(subnet_list) if subnet_list else "None"
                    
                    # Make NACL ID clickable
                    nacl_link = f'<a href="#" onclick="toggleRules(\'nacl-details-{vpc_id}-{idx}\'); return false;" style="color: #2563eb; text-decoration: underline; cursor: pointer;">{nacl_id}</a>'
                    
                    # Default badge
                    default_display = "✅ Yes" if is_default else "❌ No"
                    
                    html += f'''<tr>
                        <td><span class="code">{nacl_link}</span></td>
                        <td>{default_display}</td>
                        <td>{inbound_count}</td>
                        <td>{outbound_count}</td>
                        <td>{assoc_count}</td>
                        <td>{subnet_display}</td>
                    </tr>\n'''
                    
                    # Add expandable row for NACL details
                    html += f'''<tr id="nacl-details-{vpc_id}-{idx}" style="display:none;">
                        <td colspan="6">{generate_nacl_details(nacl)}</td>
                    </tr>\n'''
                    
                    # Add expandable rows for subnet details
                    for assoc in associations:
                        if '_full_subnet' in assoc and '_detail_id' in assoc:
                            detail_id = assoc['_detail_id']
                            full_subnet = assoc['_full_subnet']
                            html += f'''<tr id="{detail_id}" style="display:none;">
                                <td colspan="6">{generate_subnet_details(full_subnet)}</td>
                            </tr>\n'''
                
                html += '</tbody></table>\n'
                html += '</div>\n'  # Close Network ACLs collapsible section
    
    html += '</div>\n'
    return html


def generate_vpc_endpoint_details(endpoint):
    """Generate detailed drill-down for a VPC Endpoint"""
    endpoint_id = endpoint.get('VpcEndpointId', 'Unknown')
    
    html = f'''
    <div style="background-color: #f8f9fa; padding: 20px; margin: 10px 0; border-left: 4px solid #2c5aa0; border-radius: 4px;">
        <h4 style="margin-top: 0; color: #232f3e;">🔌 VPC Endpoint Details</h4>
        <table style="width: 100%; background-color: white; border-collapse: collapse; margin: 10px 0;">
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 8px; font-weight: 600; color: #546e7a; width: 250px;">Endpoint ID:</td>
                <td style="padding: 8px;"><span class="code">{endpoint_id}</span></td>
            </tr>
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 8px; font-weight: 600; color: #546e7a;">Service Name:</td>
                <td style="padding: 8px;"><span class="code">{endpoint.get('ServiceName', 'N/A')}</span></td>
            </tr>
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 8px; font-weight: 600; color: #546e7a;">Type:</td>
                <td style="padding: 8px;">{endpoint.get('VpcEndpointType', 'N/A')}</td>
            </tr>
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 8px; font-weight: 600; color: #546e7a;">State:</td>
                <td style="padding: 8px;"><span class="badge {'badge-success' if endpoint.get('State') == 'available' else 'badge-warning'}">{endpoint.get('State', 'N/A')}</span></td>
            </tr>
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 8px; font-weight: 600; color: #546e7a;">VPC ID:</td>
                <td style="padding: 8px;"><span class="code">{endpoint.get('VpcId', 'N/A')}</span></td>
            </tr>
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 8px; font-weight: 600; color: #546e7a;">Private DNS Enabled:</td>
                <td style="padding: 8px;">{'✓ Yes' if endpoint.get('PrivateDnsEnabled') else '✗ No'}</td>
            </tr>
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 8px; font-weight: 600; color: #546e7a;">Route Table IDs:</td>
                <td style="padding: 8px;">{', '.join(endpoint.get('RouteTableIds', [])) if endpoint.get('RouteTableIds') else 'None (Interface endpoint)'}</td>
            </tr>
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 8px; font-weight: 600; color: #546e7a;">Subnet IDs:</td>
                <td style="padding: 8px;">{', '.join(endpoint.get('SubnetIds', [])) if endpoint.get('SubnetIds') else 'None (Gateway endpoint)'}</td>
            </tr>
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 8px; font-weight: 600; color: #546e7a;">Security Groups:</td>
                <td style="padding: 8px;">{', '.join([sg.get('GroupId', '') for sg in endpoint.get('Groups', [])]) if endpoint.get('Groups') else 'N/A'}</td>
            </tr>
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 8px; font-weight: 600; color: #546e7a;">Network Interface IDs:</td>
                <td style="padding: 8px;">{', '.join(endpoint.get('NetworkInterfaceIds', [])) if endpoint.get('NetworkInterfaceIds') else 'N/A'}</td>
            </tr>
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 8px; font-weight: 600; color: #546e7a;">DNS Entries:</td>
                <td style="padding: 8px;">{', '.join([dns.get('DnsName', '') for dns in endpoint.get('DnsEntries', [])]) if endpoint.get('DnsEntries') else 'N/A'}</td>
            </tr>
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 8px; font-weight: 600; color: #546e7a;">Created:</td>
                <td style="padding: 8px;">{str(endpoint.get('CreationTimestamp', 'N/A'))}</td>
            </tr>
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 8px; font-weight: 600; color: #546e7a;">Owner ID:</td>
                <td style="padding: 8px;">{endpoint.get('OwnerId', 'N/A')}</td>
            </tr>
            <tr>
                <td style="padding: 8px; font-weight: 600; color: #546e7a;">Policy Document:</td>
                <td style="padding: 8px;"><pre style="background: #f5f5f5; padding: 10px; border-radius: 4px; overflow-x: auto; font-size: 11px;">{json.dumps(json.loads(endpoint.get('PolicyDocument', '{}')), indent=2) if endpoint.get('PolicyDocument') else 'Default policy'}</pre></td>
            </tr>
        </table>
        
        {'<h5 style="color: #232f3e; margin-top: 20px;">📋 Tags</h5>' if endpoint.get('Tags') else ''}
        {generate_tags_table(endpoint.get('Tags', [])) if endpoint.get('Tags') else ''}
    </div>
    '''
    return html


def generate_vpc_peering_details(peering):
    """Generate detailed drill-down for a VPC Peering Connection"""
    peering_id = peering.get('VpcPeeringConnectionId', 'Unknown')
    
    requester_info = peering.get('RequesterVpcInfo', {})
    accepter_info = peering.get('AccepterVpcInfo', {})
    status_info = peering.get('Status', {})
    
    html = f'''
    <div style="background-color: #f8f9fa; padding: 20px; margin: 10px 0; border-left: 4px solid #FF9900; border-radius: 4px;">
        <h4 style="margin-top: 0; color: #232f3e;">🔄 VPC Peering Connection Details</h4>
        <table style="width: 100%; background-color: white; border-collapse: collapse; margin: 10px 0;">
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 8px; font-weight: 600; color: #546e7a; width: 250px;">Peering Connection ID:</td>
                <td style="padding: 8px;"><span class="code">{peering_id}</span></td>
            </tr>
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 8px; font-weight: 600; color: #546e7a;">Status:</td>
                <td style="padding: 8px;"><span class="badge {'badge-success' if status_info.get('Code') == 'active' else 'badge-warning'}">{status_info.get('Code', 'N/A')}</span> - {status_info.get('Message', '')}</td>
            </tr>
        </table>
        
        <h5 style="color: #232f3e; margin-top: 20px;">📤 Requester VPC</h5>
        <table style="width: 100%; background-color: white; border-collapse: collapse; margin: 10px 0;">
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 8px; font-weight: 600; color: #546e7a; width: 250px;">VPC ID:</td>
                <td style="padding: 8px;"><span class="code">{requester_info.get('VpcId', 'N/A')}</span></td>
            </tr>
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 8px; font-weight: 600; color: #546e7a;">CIDR Block:</td>
                <td style="padding: 8px;">{requester_info.get('CidrBlock', 'N/A')}</td>
            </tr>
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 8px; font-weight: 600; color: #546e7a;">Owner ID:</td>
                <td style="padding: 8px;">{requester_info.get('OwnerId', 'N/A')}</td>
            </tr>
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 8px; font-weight: 600; color: #546e7a;">Region:</td>
                <td style="padding: 8px;">{requester_info.get('Region', 'N/A')}</td>
            </tr>
            <tr>
                <td style="padding: 8px; font-weight: 600; color: #546e7a;">IPv6 CIDR Blocks:</td>
                <td style="padding: 8px;">{', '.join([cidr.get('Ipv6CidrBlock', '') for cidr in requester_info.get('Ipv6CidrBlockSet', [])]) if requester_info.get('Ipv6CidrBlockSet') else 'None'}</td>
            </tr>
        </table>
        
        <h5 style="color: #232f3e; margin-top: 20px;">📥 Accepter VPC</h5>
        <table style="width: 100%; background-color: white; border-collapse: collapse; margin: 10px 0;">
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 8px; font-weight: 600; color: #546e7a; width: 250px;">VPC ID:</td>
                <td style="padding: 8px;"><span class="code">{accepter_info.get('VpcId', 'N/A')}</span></td>
            </tr>
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 8px; font-weight: 600; color: #546e7a;">CIDR Block:</td>
                <td style="padding: 8px;">{accepter_info.get('CidrBlock', 'N/A')}</td>
            </tr>
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 8px; font-weight: 600; color: #546e7a;">Owner ID:</td>
                <td style="padding: 8px;">{accepter_info.get('OwnerId', 'N/A')}</td>
            </tr>
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 8px; font-weight: 600; color: #546e7a;">Region:</td>
                <td style="padding: 8px;">{accepter_info.get('Region', 'N/A')}</td>
            </tr>
            <tr>
                <td style="padding: 8px; font-weight: 600; color: #546e7a;">IPv6 CIDR Blocks:</td>
                <td style="padding: 8px;">{', '.join([cidr.get('Ipv6CidrBlock', '') for cidr in accepter_info.get('Ipv6CidrBlockSet', [])]) if accepter_info.get('Ipv6CidrBlockSet') else 'None'}</td>
            </tr>
        </table>
        
        <h5 style="color: #232f3e; margin-top: 20px;">⚙️ Peering Options</h5>
        <table style="width: 100%; background-color: white; border-collapse: collapse; margin: 10px 0;">
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 8px; font-weight: 600; color: #546e7a; width: 250px;">Allow DNS Resolution (Requester → Accepter):</td>
                <td style="padding: 8px;">{'✓ Yes' if requester_info.get('PeeringOptions', {}).get('AllowDnsResolutionFromRemoteVpc') else '✗ No'}</td>
            </tr>
            <tr>
                <td style="padding: 8px; font-weight: 600; color: #546e7a;">Allow DNS Resolution (Accepter → Requester):</td>
                <td style="padding: 8px;">{'✓ Yes' if accepter_info.get('PeeringOptions', {}).get('AllowDnsResolutionFromRemoteVpc') else '✗ No'}</td>
            </tr>
        </table>
        
        {'<h5 style="color: #232f3e; margin-top: 20px;">📋 Tags</h5>' if peering.get('Tags') else ''}
        {generate_tags_table(peering.get('Tags', [])) if peering.get('Tags') else ''}
    </div>
    '''
    return html


def generate_tags_table(tags):
    """Generate a formatted table for tags"""
    if not tags:
        return '<p>No tags</p>'
    
    html = '<table style="width: 100%; background-color: white; border-collapse: collapse; margin: 10px 0;">\n'
    html += '<thead><tr style="background-color: #f5f5f5;"><th style="padding: 8px; text-align: left;">Key</th><th style="padding: 8px; text-align: left;">Value</th></tr></thead>\n'
    html += '<tbody>\n'
    
    for tag in tags:
        key = tag.get('Key', '')
        value = tag.get('Value', '')
        html += f'<tr style="border-bottom: 1px solid #ddd;"><td style="padding: 8px;">{key}</td><td style="padding: 8px;">{value}</td></tr>\n'
    
    html += '</tbody></table>\n'
    return html


def generate_igw_details(igw):
    """Generate detailed information for an Internet Gateway"""
    if not igw:
        return '<p>No Internet Gateway details available</p>'
    
    igw_id = igw.get('InternetGatewayId', 'Unknown')
    
    html = f'<div style="margin: 15px 0; padding: 15px; background-color: #f9fafb; border-left: 4px solid #3b82f6; border-radius: 4px;">\n'
    html += f'<h4 style="margin: 0 0 10px 0; color: #1e40af;">Internet Gateway: {igw_id}</h4>\n'
    
    # Attachments
    attachments = igw.get('Attachments', [])
    if attachments:
        html += '<p style="margin: 10px 0;"><strong>Attachments:</strong></p>\n'
        html += '<ul style="margin: 5px 0; padding-left: 20px;">\n'
        for attachment in attachments:
            vpc_id = attachment.get('VpcId', 'Unknown')
            state = attachment.get('State', 'Unknown')
            html += f'<li>VPC: {vpc_id} - State: {state}</li>\n'
        html += '</ul>\n'
    else:
        html += '<p style="margin: 10px 0;">No VPC attachments</p>\n'
    
    # Owner ID
    owner_id = igw.get('OwnerId', 'Unknown')
    html += f'<p style="margin: 10px 0;"><strong>Owner ID:</strong> {owner_id}</p>\n'
    
    # Tags
    tags = igw.get('Tags', [])
    if tags:
        html += '<p style="margin: 10px 0;"><strong>Tags:</strong></p>\n'
        html += generate_tags_table(tags)
    
    html += '</div>\n'
    return html


def generate_route_table_details(rt):
    """Generate detailed information for a Route Table"""
    if not rt:
        return '<p>No Route Table details available</p>'
    
    rt_id = rt.get('RouteTableId', 'Unknown')
    vpc_id = rt.get('VpcId', 'Unknown')
    
    html = f'<div style="margin: 15px 0; padding: 15px; background-color: #f9fafb; border-left: 4px solid #8b5cf6; border-radius: 4px;">\n'
    html += f'<h4 style="margin: 0 0 10px 0; color: #6d28d9;">Route Table: {rt_id}</h4>\n'
    html += f'<p style="margin: 10px 0;"><strong>VPC:</strong> {vpc_id}</p>\n'
    
    # Routes
    routes = rt.get('Routes', [])
    if routes:
        html += '<p style="margin: 10px 0;"><strong>Routes:</strong></p>\n'
        html += '<table style="width: 100%; background-color: white; border-collapse: collapse; margin: 10px 0;">\n'
        html += '<thead><tr style="background-color: #f5f5f5;">'
        html += '<th style="padding: 8px; text-align: left;">Destination</th>'
        html += '<th style="padding: 8px; text-align: left;">Target</th>'
        html += '<th style="padding: 8px; text-align: left;">Status</th>'
        html += '<th style="padding: 8px; text-align: left;">Origin</th>'
        html += '</tr></thead>\n<tbody>\n'
        
        for route in routes:
            dest = route.get('DestinationCidrBlock') or route.get('DestinationIpv6CidrBlock') or route.get('DestinationPrefixListId', 'Unknown')
            target = (route.get('GatewayId') or route.get('NatGatewayId') or 
                     route.get('NetworkInterfaceId') or route.get('VpcPeeringConnectionId') or 
                     route.get('TransitGatewayId') or route.get('LocalGatewayId') or 'Unknown')
            state = route.get('State', 'Unknown')
            origin = route.get('Origin', 'Unknown')
            
            html += f'<tr style="border-bottom: 1px solid #ddd;">'
            html += f'<td style="padding: 8px;">{dest}</td>'
            html += f'<td style="padding: 8px;">{target}</td>'
            html += f'<td style="padding: 8px;">{state}</td>'
            html += f'<td style="padding: 8px;">{origin}</td>'
            html += '</tr>\n'
        
        html += '</tbody></table>\n'
    
    # Associations
    associations = rt.get('Associations', [])
    if associations:
        html += '<p style="margin: 10px 0;"><strong>Associations:</strong></p>\n'
        html += '<table style="width: 100%; background-color: white; border-collapse: collapse; margin: 10px 0;">\n'
        html += '<thead><tr style="background-color: #f5f5f5;">'
        html += '<th style="padding: 8px; text-align: left;">Association ID</th>'
        html += '<th style="padding: 8px; text-align: left;">Associated With</th>'
        html += '<th style="padding: 8px; text-align: left;">Main</th>'
        html += '</tr></thead>\n<tbody>\n'
        
        for assoc in associations:
            assoc_id = assoc.get('RouteTableAssociationId', 'Unknown')
            subnet_id = assoc.get('SubnetId', '')
            gateway_id = assoc.get('GatewayId', '')
            is_main = 'Yes' if assoc.get('Main', False) else 'No'
            
            associated_with = subnet_id or gateway_id or 'Unknown'
            
            html += f'<tr style="border-bottom: 1px solid #ddd;">'
            html += f'<td style="padding: 8px;">{assoc_id}</td>'
            html += f'<td style="padding: 8px;">{associated_with}</td>'
            html += f'<td style="padding: 8px;">{is_main}</td>'
            html += '</tr>\n'
        
        html += '</tbody></table>\n'
    
    # Tags
    tags = rt.get('Tags', [])
    if tags:
        html += '<p style="margin: 10px 0;"><strong>Tags:</strong></p>\n'
        html += generate_tags_table(tags)
    
    html += '</div>\n'
    return html


def generate_subnet_details(subnet):
    """Generate detailed information for a Subnet"""
    if not subnet:
        return '<p>No Subnet details available</p>'
    
    subnet_id = subnet.get('SubnetId', 'Unknown')
    vpc_id = subnet.get('VpcId', 'Unknown')
    az = subnet.get('AvailabilityZone', 'Unknown')
    cidr = subnet.get('CidrBlock', 'Unknown')
    
    html = f'<div style="margin: 15px 0; padding: 15px; background-color: #f9fafb; border-left: 4px solid #10b981; border-radius: 4px;">\n'
    html += f'<h4 style="margin: 0 0 10px 0; color: #059669;">Subnet: {subnet_id}</h4>\n'
    
    # Basic Info
    html += f'<p style="margin: 10px 0;"><strong>VPC:</strong> {vpc_id}</p>\n'
    html += f'<p style="margin: 10px 0;"><strong>Availability Zone:</strong> {az}</p>\n'
    html += f'<p style="margin: 10px 0;"><strong>CIDR Block:</strong> <span class="code">{cidr}</span></p>\n'
    
    # State and attributes
    state = subnet.get('State', 'Unknown')
    available_ips = subnet.get('AvailableIpAddressCount', 'Unknown')
    map_public_ip = subnet.get('MapPublicIpOnLaunch', False)
    
    html += f'<p style="margin: 10px 0;"><strong>State:</strong> {state}</p>\n'
    html += f'<p style="margin: 10px 0;"><strong>Available IP Addresses:</strong> {available_ips}</p>\n'
    html += f'<p style="margin: 10px 0;"><strong>Auto-assign Public IP:</strong> {"Yes" if map_public_ip else "No"}</p>\n'
    
    # IPv6 if present
    ipv6_cidr = subnet.get('Ipv6CidrBlockAssociationSet', [])
    if ipv6_cidr:
        html += '<p style="margin: 10px 0;"><strong>IPv6 CIDR Blocks:</strong></p>\n'
        html += '<ul style="margin: 5px 0; padding-left: 20px;">\n'
        for ipv6 in ipv6_cidr:
            ipv6_block = ipv6.get('Ipv6CidrBlock', 'Unknown')
            ipv6_state = ipv6.get('Ipv6CidrBlockState', {}).get('State', 'Unknown')
            html += f'<li><span class="code">{ipv6_block}</span> - {ipv6_state}</li>\n'
        html += '</ul>\n'
    
    # Tags
    tags = subnet.get('Tags', [])
    if tags:
        html += '<p style="margin: 10px 0;"><strong>Tags:</strong></p>\n'
        html += generate_tags_table(tags)
    
    html += '</div>\n'
    return html


def generate_nacl_details(nacl):
    """Generate detailed information for a Network ACL"""
    if not nacl:
        return '<p>No Network ACL details available</p>'
    
    nacl_id = nacl.get('NetworkAclId', 'Unknown')
    vpc_id = nacl.get('VpcId', 'Unknown')
    is_default = nacl.get('IsDefault', False)
    
    html = f'<div style="margin: 15px 0; padding: 15px; background-color: #f9fafb; border-left: 4px solid #f59e0b; border-radius: 4px;">\n'
    html += f'<h4 style="margin: 0 0 10px 0; color: #d97706;">Network ACL: {nacl_id}</h4>\n'
    
    # Basic Info
    html += f'<p style="margin: 10px 0;"><strong>VPC:</strong> {vpc_id}</p>\n'
    html += f'<p style="margin: 10px 0;"><strong>Default NACL:</strong> {"Yes" if is_default else "No"}</p>\n'
    
    # Inbound Rules
    entries = nacl.get('Entries', [])
    inbound_rules = [e for e in entries if not e.get('Egress', False)]
    outbound_rules = [e for e in entries if e.get('Egress', False)]
    
    if inbound_rules:
        html += '<p style="margin: 15px 0 5px 0;"><strong>Inbound Rules:</strong></p>\n'
        html += '<table style="width: 100%; background-color: white; border-collapse: collapse; margin: 10px 0; font-size: 12px;">\n'
        html += '<thead><tr style="background-color: #f5f5f5;">'
        html += '<th style="padding: 8px; text-align: left;">Rule #</th>'
        html += '<th style="padding: 8px; text-align: left;">Action</th>'
        html += '<th style="padding: 8px; text-align: left;">Protocol</th>'
        html += '<th style="padding: 8px; text-align: left;">Port Range</th>'
        html += '<th style="padding: 8px; text-align: left;">Source</th>'
        html += '</tr></thead>\n<tbody>\n'
        
        for rule in sorted(inbound_rules, key=lambda x: x.get('RuleNumber', 999)):
            rule_num = rule.get('RuleNumber', 'N/A')
            action = rule.get('RuleAction', 'N/A')
            protocol = rule.get('Protocol', 'N/A')
            
            # Protocol mapping
            if protocol == '-1':
                protocol_str = 'All'
            elif protocol == '6':
                protocol_str = 'TCP'
            elif protocol == '17':
                protocol_str = 'UDP'
            elif protocol == '1':
                protocol_str = 'ICMP'
            else:
                protocol_str = protocol
            
            # Port range
            port_from = rule.get('PortRange', {}).get('From', '')
            port_to = rule.get('PortRange', {}).get('To', '')
            if port_from and port_to:
                if port_from == port_to:
                    port_range = str(port_from)
                else:
                    port_range = f"{port_from}-{port_to}"
            else:
                port_range = 'All'
            
            cidr = rule.get('CidrBlock') or rule.get('Ipv6CidrBlock', 'N/A')
            
            # Color code action
            action_color = '#10b981' if action.lower() == 'allow' else '#ef4444'
            action_display = f'<span style="color: {action_color}; font-weight: 600;">{action.upper()}</span>'
            
            html += f'<tr style="border-bottom: 1px solid #ddd;">'
            html += f'<td style="padding: 8px;">{rule_num}</td>'
            html += f'<td style="padding: 8px;">{action_display}</td>'
            html += f'<td style="padding: 8px;">{protocol_str}</td>'
            html += f'<td style="padding: 8px;">{port_range}</td>'
            html += f'<td style="padding: 8px;"><span class="code">{cidr}</span></td>'
            html += '</tr>\n'
        
        html += '</tbody></table>\n'
    
    # Outbound Rules
    if outbound_rules:
        html += '<p style="margin: 15px 0 5px 0;"><strong>Outbound Rules:</strong></p>\n'
        html += '<table style="width: 100%; background-color: white; border-collapse: collapse; margin: 10px 0; font-size: 12px;">\n'
        html += '<thead><tr style="background-color: #f5f5f5;">'
        html += '<th style="padding: 8px; text-align: left;">Rule #</th>'
        html += '<th style="padding: 8px; text-align: left;">Action</th>'
        html += '<th style="padding: 8px; text-align: left;">Protocol</th>'
        html += '<th style="padding: 8px; text-align: left;">Port Range</th>'
        html += '<th style="padding: 8px; text-align: left;">Destination</th>'
        html += '</tr></thead>\n<tbody>\n'
        
        for rule in sorted(outbound_rules, key=lambda x: x.get('RuleNumber', 999)):
            rule_num = rule.get('RuleNumber', 'N/A')
            action = rule.get('RuleAction', 'N/A')
            protocol = rule.get('Protocol', 'N/A')
            
            # Protocol mapping
            if protocol == '-1':
                protocol_str = 'All'
            elif protocol == '6':
                protocol_str = 'TCP'
            elif protocol == '17':
                protocol_str = 'UDP'
            elif protocol == '1':
                protocol_str = 'ICMP'
            else:
                protocol_str = protocol
            
            # Port range
            port_from = rule.get('PortRange', {}).get('From', '')
            port_to = rule.get('PortRange', {}).get('To', '')
            if port_from and port_to:
                if port_from == port_to:
                    port_range = str(port_from)
                else:
                    port_range = f"{port_from}-{port_to}"
            else:
                port_range = 'All'
            
            cidr = rule.get('CidrBlock') or rule.get('Ipv6CidrBlock', 'N/A')
            
            # Color code action
            action_color = '#10b981' if action.lower() == 'allow' else '#ef4444'
            action_display = f'<span style="color: {action_color}; font-weight: 600;">{action.upper()}</span>'
            
            html += f'<tr style="border-bottom: 1px solid #ddd;">'
            html += f'<td style="padding: 8px;">{rule_num}</td>'
            html += f'<td style="padding: 8px;">{action_display}</td>'
            html += f'<td style="padding: 8px;">{protocol_str}</td>'
            html += f'<td style="padding: 8px;">{port_range}</td>'
            html += f'<td style="padding: 8px;"><span class="code">{cidr}</span></td>'
            html += '</tr>\n'
        
        html += '</tbody></table>\n'
    
    # Tags
    tags = nacl.get('Tags', [])
    if tags:
        html += '<p style="margin: 10px 0;"><strong>Tags:</strong></p>\n'
        html += generate_tags_table(tags)
    
    html += '</div>\n'
    return html


def analyze_security_group_rule_compliance(rule, rule_type='ingress'):
    """
    Analyze a security group rule for compliance issues.
    
    Compliance checks:
    - 0.0.0.0/0 on sensitive ports (22, 3389, 1433, 3306, 5432, etc.) = CRITICAL
    - 0.0.0.0/0 on any port = HIGH (unless HTTPS 443 for public services)
    - Overly broad CIDR ranges (/8, /16) = MEDIUM
    - Port ranges larger than 100 ports = LOW
    
    Returns: dict with is_compliant, severity, issue_description, recommendation
    """
    issues = []
    severity = 'COMPLIANT'
    
    # Sensitive ports that should NEVER be open to 0.0.0.0/0
    sensitive_ports = {
        22: 'SSH',
        3389: 'RDP',
        1433: 'MS SQL',
        3306: 'MySQL',
        5432: 'PostgreSQL',
        5984: 'CouchDB',
        6379: 'Redis',
        7001: 'Cassandra',
        8020: 'Hadoop',
        8888: 'Jupyter',
        9042: 'Cassandra',
        9200: 'Elasticsearch',
        11211: 'Memcached',
        27017: 'MongoDB'
    }
    
    protocol = rule.get('IpProtocol', 'unknown')
    from_port = rule.get('FromPort', 'All')
    to_port = rule.get('ToPort', 'All')
    
    # Check IP ranges
    for ip_range in rule.get('IpRanges', []):
        cidr = ip_range.get('CidrIp', '')
        description = ip_range.get('Description', 'No description')
        
        # Check for 0.0.0.0/0
        if cidr == '0.0.0.0/0':
            # Check if it's a sensitive port
            if from_port in sensitive_ports:
                severity = 'CRITICAL'
                issues.append(f"❌ CRITICAL: Port {from_port} ({sensitive_ports[from_port]}) open to entire internet (0.0.0.0/0)")
            elif from_port != 443 and from_port != 80:  # Allow 80/443 for public web services
                severity = 'HIGH' if severity != 'CRITICAL' else severity
                issues.append(f"⚠️ HIGH: Port {from_port}-{to_port} open to entire internet (0.0.0.0/0)")
            elif from_port in [80, 443]:
                issues.append(f"ℹ️ INFO: Public web port {from_port} open to internet (typical for web services)")
        
        # Check for overly broad CIDR ranges
        elif '/' in cidr:
            prefix = int(cidr.split('/')[1])
            if prefix <= 8:
                severity = 'MEDIUM' if severity not in ['CRITICAL', 'HIGH'] else severity
                issues.append(f"⚠️ MEDIUM: Very broad CIDR range {cidr} (/{prefix}) allows ~16 million IPs")
            elif prefix <= 16:
                severity = 'LOW' if severity not in ['CRITICAL', 'HIGH', 'MEDIUM'] else severity
                issues.append(f"⚠️ LOW: Broad CIDR range {cidr} (/{prefix}) allows ~65k IPs")
    
    # Check for large port ranges
    if from_port != 'All' and to_port != 'All':
        port_range = to_port - from_port + 1
        if port_range > 100:
            severity = 'LOW' if severity not in ['CRITICAL', 'HIGH', 'MEDIUM'] else severity
            issues.append(f"⚠️ LOW: Large port range ({from_port}-{to_port} = {port_range} ports)")
    
    # Check for 'All' protocols
    if protocol == '-1':
        severity = 'MEDIUM' if severity not in ['CRITICAL', 'HIGH'] else severity
        issues.append(f"⚠️ MEDIUM: All protocols allowed (should restrict to specific protocols)")
    
    is_compliant = len(issues) == 0
    
    recommendations = []
    if not is_compliant:
        if any('0.0.0.0/0' in issue for issue in issues):
            recommendations.append("🔒 Restrict source to specific IP ranges or security groups")
            recommendations.append("🔒 Use VPN or bastion hosts for administrative access")
        if any('CIDR range' in issue for issue in issues):
            recommendations.append("🔒 Narrow CIDR ranges to minimum required IPs")
        if any('port range' in issue for issue in issues):
            recommendations.append("🔒 Limit port ranges to only required ports")
        if any('All protocols' in issue for issue in issues):
            recommendations.append("🔒 Specify exact protocols (TCP/UDP/ICMP)")
    
    return {
        'is_compliant': is_compliant,
        'severity': severity,
        'issues': issues,
        'recommendations': recommendations
    }


def sort_rules_by_severity(rules, rule_type='ingress'):
    """
    Sort security group rules by severity (CRITICAL → HIGH → MEDIUM → LOW → COMPLIANT).
    
    Args:
        rules: List of IpPermissions or IpPermissionsEgress rule objects
        rule_type: 'ingress' or 'egress'
    
    Returns:
        Sorted list of rules
    """
    severity_order = {
        'CRITICAL': 0,
        'HIGH': 1,
        'MEDIUM': 2,
        'LOW': 3,
        'COMPLIANT': 4
    }
    
    # Add severity to each rule for sorting
    rules_with_severity = []
    for rule in rules:
        compliance = analyze_security_group_rule_compliance(rule, rule_type)
        rules_with_severity.append({
            'rule': rule,
            'severity': compliance['severity'],
            'severity_rank': severity_order.get(compliance['severity'], 999)
        })
    
    # Sort by severity rank
    rules_with_severity.sort(key=lambda x: x['severity_rank'])
    
    # Return just the rules
    return [item['rule'] for item in rules_with_severity]


def format_security_group_rule(rule, rule_type='ingress', start_counter=1):
    """Format a security group rule for display with compliance analysis
    
    Each destination (IP range, SG reference, IPv6 range, prefix list) is shown as a separate numbered rule.
    This matches how AWS console displays rules and how the verification script counts them.
    
    Args:
        rule: The IpPermissions or IpPermissionsEgress rule object
        rule_type: 'ingress' or 'egress'
        start_counter: The starting number for rules (allows continuous numbering across multiple rules)
    
    Returns:
        tuple: (html_string, next_counter) where next_counter is the number to use for the next rule
    """
    protocol = rule.get('IpProtocol', '-1')
    from_port = rule.get('FromPort', 'All')
    to_port = rule.get('ToPort', 'All')
    
    # Protocol display
    if protocol == '-1':
        proto_display = 'All'
    elif protocol == '6':
        proto_display = 'TCP'
    elif protocol == '17':
        proto_display = 'UDP'
    elif protocol == '1':
        proto_display = 'ICMP'
    else:
        proto_display = protocol.upper() if isinstance(protocol, str) else str(protocol)
    
    # Port display - detect "All Ports" 
    if from_port == 'All':
        port_display = 'All Ports'
    elif from_port == 0 and to_port == 65535:
        port_display = 'All Ports (0-65535)'
    elif from_port == to_port:
        port_display = str(from_port)
    else:
        port_display = f"{from_port}-{to_port}"
    
    # Type field (for AWS console compatibility)
    type_display = ''
    if rule_type == 'ingress':
        if protocol == '1':  # ICMP
            type_display = 'Echo Reply' if from_port == 0 else 'All ICMP'
        else:
            type_display = 'HTTPS' if from_port == 443 and to_port == 443 else \
                          'HTTP' if from_port == 80 and to_port == 80 else \
                          'SSH' if from_port == 22 and to_port == 22 else \
                          'All TCP' if from_port == 0 and to_port == 65535 and protocol == '6' else \
                          proto_display
    
    # Analyze compliance
    compliance = analyze_security_group_rule_compliance(rule, rule_type)
    
    # Use correct label based on rule type
    target_label = "Source" if rule_type == 'ingress' else "Destination"
    
    # Compliance badge
    severity_badge = {
        'CRITICAL': 'badge-danger',
        'HIGH': 'badge-danger',
        'MEDIUM': 'badge-warning',
        'LOW': 'badge-info',
        'COMPLIANT': 'badge-success'
    }.get(compliance['severity'], 'badge-success')
    
    compliance_badge = f'<span class="badge {severity_badge}">{compliance["severity"]}</span>'
    
    # Format issues and recommendations (same for all destinations in this rule)
    issues_html = ''
    if not compliance['is_compliant']:
        issues_html = '<div style="margin-top: 8px; padding: 8px; background: #fff3cd; border-left: 3px solid #ffc107; border-radius: 3px;">'
        issues_html += '<strong>Issues:</strong><br>'
        issues_html += '<br>'.join(compliance['issues'])
        if compliance['recommendations']:
            issues_html += '<br><br><strong>Recommendations:</strong><br>'
            issues_html += '<br>'.join(compliance['recommendations'])
        issues_html += '</div>'
    
    # Build individual rule entries for each destination
    rule_entries = []
    rule_counter = start_counter
    
    # IP Ranges (IPv4)
    for ip_range in rule.get('IpRanges', []):
        cidr = ip_range.get('CidrIp', '')
        desc = ip_range.get('Description', '')
        target_display = f"{cidr}" + (f" ({desc})" if desc else "")
        ip_version = 'IPv4'
        
        rule_entries.append(f'''
        <div style="padding: 10px; margin: 5px 0; background: #f9f9f9; border-radius: 4px; border-left: 3px solid {"#dc3545" if not compliance["is_compliant"] else "#28a745"};">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <strong>Rule {rule_counter}:</strong> {proto_display} &nbsp;|&nbsp; 
                    <strong>Port:</strong> {port_display} &nbsp;|&nbsp; 
                    {f'<strong>Type:</strong> {type_display} &nbsp;|&nbsp; ' if type_display else ''}
                    <strong>IP Version:</strong> {ip_version} &nbsp;|&nbsp; 
                    <strong>{target_label}:</strong> {target_display}
                </div>
                <div>{compliance_badge}</div>
            </div>
        </div>
        ''')
        rule_counter += 1
    
    # Security Group References
    for sg_ref in rule.get('UserIdGroupPairs', []):
        sg_id = sg_ref.get('GroupId', '')
        desc = sg_ref.get('Description', '')
        target_display = f"sg: {sg_id}" + (f" ({desc})" if desc else "")
        
        rule_entries.append(f'''
        <div style="padding: 10px; margin: 5px 0; background: #f9f9f9; border-radius: 4px; border-left: 3px solid {"#dc3545" if not compliance["is_compliant"] else "#28a745"};">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <strong>Rule {rule_counter}:</strong> {proto_display} &nbsp;|&nbsp; 
                    <strong>Port:</strong> {port_display} &nbsp;|&nbsp; 
                    {f'<strong>Type:</strong> {type_display} &nbsp;|&nbsp; ' if type_display else ''}
                    <strong>{target_label}:</strong> {target_display}
                </div>
                <div>{compliance_badge}</div>
            </div>
        </div>
        ''')
        rule_counter += 1
    
    # IPv6 Ranges
    for ipv6_range in rule.get('Ipv6Ranges', []):
        cidr = ipv6_range.get('CidrIpv6', '')
        desc = ipv6_range.get('Description', '')
        target_display = f"{cidr}" + (f" ({desc})" if desc else "")
        ip_version = 'IPv6'
        
        rule_entries.append(f'''
        <div style="padding: 10px; margin: 5px 0; background: #f9f9f9; border-radius: 4px; border-left: 3px solid {"#dc3545" if not compliance["is_compliant"] else "#28a745"};">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <strong>Rule {rule_counter}:</strong> {proto_display} &nbsp;|&nbsp; 
                    <strong>Port:</strong> {port_display} &nbsp;|&nbsp; 
                    {f'<strong>Type:</strong> {type_display} &nbsp;|&nbsp; ' if type_display else ''}
                    <strong>IP Version:</strong> {ip_version} &nbsp;|&nbsp; 
                    <strong>{target_label}:</strong> {target_display}
                </div>
                <div>{compliance_badge}</div>
            </div>
        </div>
        ''')
        rule_counter += 1
    
    # Prefix Lists (VPC Endpoints)
    for prefix_list in rule.get('PrefixListIds', []):
        pl_id = prefix_list.get('PrefixListId', '') if isinstance(prefix_list, dict) else prefix_list
        desc = prefix_list.get('Description', '') if isinstance(prefix_list, dict) else ''
        target_display = f"pl: {pl_id}" + (f" ({desc})" if desc else " (VPC Endpoint)")
        
        rule_entries.append(f'''
        <div style="padding: 10px; margin: 5px 0; background: #f9f9f9; border-radius: 4px; border-left: 3px solid {"#dc3545" if not compliance["is_compliant"] else "#28a745"};">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <strong>Rule {rule_counter}:</strong> {proto_display} &nbsp;|&nbsp; 
                    <strong>Port:</strong> {port_display} &nbsp;|&nbsp; 
                    {f'<strong>Type:</strong> {type_display} &nbsp;|&nbsp; ' if type_display else ''}
                    <strong>{target_label}:</strong> {target_display}
                </div>
                <div>{compliance_badge}</div>
            </div>
        </div>
        ''')
        rule_counter += 1
    
    # If no destinations found, show a default entry
    if not rule_entries:
        rule_entries.append(f'''
        <div style="padding: 10px; margin: 5px 0; background: #f9f9f9; border-radius: 4px; border-left: 3px solid #6c757d;">
            <div>
                <strong>Rule {rule_counter}:</strong> {proto_display} &nbsp;|&nbsp; 
                <strong>Port:</strong> {port_display} &nbsp;|&nbsp; 
                <strong>{target_label}:</strong> None
            </div>
        </div>
        ''')
        rule_counter += 1
    
    # Add issues/recommendations ONCE at the end (applies to all destinations above)
    if issues_html:
        rule_entries.append(issues_html)
    
    return (''.join(rule_entries), rule_counter)


def generate_security_groups_section(sg_data):
    """Generate HTML for security groups section with detailed rule analysis and network graph"""
    if not sg_data or 'checks' not in sg_data:
        return ""
    
    # Try to get raw security group data for the network graph
    raw_security_groups = sg_data.get('raw_data', {}).get('SecurityGroups', [])
    
    html = '<div class="section">\n'
    html += '<h2>Security Groups</h2>\n'
    
    # Add network visualization if we have raw data
    if raw_security_groups and len(raw_security_groups) > 0:
        # Create JSON data for D3 graph
        import json as json_lib
        sg_json = json_lib.dumps(raw_security_groups)
        
        html += '''
<div class="graph-controls">
    <div class="legend-item">
        <strong>Network Visualization:</strong> <span style="font-size: 0.9em; color: #666;">(Interactive - drag nodes, click to filter)</span>
    </div>
    <button onclick="resetGraph()">Reset View</button>
    <button onclick="filterInternetExposed()">Internet-Exposed Only</button>
    <button onclick="filterPermissive()">Show Overly Permissive</button>
    <label style="margin-left: 15px;">
        Port Filter: <input type="text" id="portFilter" placeholder="e.g., 22, 443" style="width: 100px; padding: 3px;">
        <button onclick="filterByPort()">Apply</button>
    </label>
    <label style="margin-left: 15px;">
        <input type="checkbox" id="showIngress" onchange="toggleIngress()" checked> Show Ingress
    </label>
    <label style="margin-left: 15px;">
        <input type="checkbox" id="showEgress" onchange="toggleEgress()" checked> Show Egress
    </label>
    <div class="graph-legend">
        <div class="legend-item">
            <div class="legend-color" style="background: #dc3545;"></div>
            <span>From Internet (0.0.0.0/0)</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background: #28a745;"></div>
            <span>Ingress (SG-to-SG)</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background: #4e8ac9;"></div>
            <span>Egress (SG→SG)</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background: #9b59b6; clip-path: polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%);"></div>
            <span>VPC Endpoints</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background: #ff6b6b; border: 2px dashed #000;"></div>
            <span>All Ports/Protocols</span>
        </div>
    </div>
</div>
<div id="sg-network-graph"></div>
<script>
    // Security Groups data from AWS
    const securityGroupsData = ''' + sg_json + ''';
    
    // Will be initialized after page load
    let sgGraphInitialized = false;
    
    function initSecurityGroupGraph() {
        if (sgGraphInitialized) return;
        sgGraphInitialized = true;
        
        // Debug logging
        console.log('Initializing security group graph');
        console.log('Security groups data:', securityGroupsData);
        console.log('Number of security groups:', securityGroupsData.length);
        
        if (!securityGroupsData || securityGroupsData.length === 0) {
            console.error('No security groups data available');
            document.getElementById('sg-network-graph').innerHTML = 
                '<div style="padding: 20px; text-align: center; color: #666;">No security groups found in data</div>';
            return;
        }
        
        const width = document.getElementById('sg-network-graph').offsetWidth;
        const height = 600;
        
        console.log('Graph dimensions:', width, 'x', height);
        
        // Transform AWS data into nodes and links
        const nodes = [];
        const links = [];
        const nodeMap = new Map();
        
        // Create nodes for each security group
        securityGroupsData.forEach((sg, idx) => {
            // Count individual permission entries (match AWS console and verification script)
            let ingressCount = 0;
            if (sg.IpPermissions) {
                sg.IpPermissions.forEach(rule => {
                    ingressCount += (rule.UserIdGroupPairs || []).length;
                    ingressCount += (rule.IpRanges || []).length;
                    ingressCount += (rule.Ipv6Ranges || []).length;
                    ingressCount += (rule.PrefixListIds || []).length;
                });
                if (ingressCount === 0 && sg.IpPermissions.length > 0) ingressCount = sg.IpPermissions.length;
            }
            
            let egressCount = 0;
            if (sg.IpPermissionsEgress) {
                sg.IpPermissionsEgress.forEach(rule => {
                    egressCount += (rule.UserIdGroupPairs || []).length;
                    egressCount += (rule.IpRanges || []).length;
                    egressCount += (rule.Ipv6Ranges || []).length;
                    egressCount += (rule.PrefixListIds || []).length;
                });
                if (egressCount === 0 && sg.IpPermissionsEgress.length > 0) egressCount = sg.IpPermissionsEgress.length;
            }
            
            const node = {
                id: sg.GroupId,
                name: sg.GroupName || sg.GroupId,
                vpcId: sg.VpcId,
                description: sg.Description,
                ingressCount: ingressCount,
                egressCount: egressCount,
                totalRules: ingressCount + egressCount,
                hasInternetAccess: false,
                hasPermissiveRules: false
            };
            nodes.push(node);
            nodeMap.set(sg.GroupId, node);
        });
        
        // Create links from rules
        securityGroupsData.forEach(sg => {
            // Process ingress rules
            if (sg.IpPermissions) {
                sg.IpPermissions.forEach(rule => {
                    const protocol = rule.IpProtocol === '-1' ? 'All' : rule.IpProtocol.toUpperCase();
                    const portRange = rule.FromPort === rule.ToPort ? 
                        `${rule.FromPort || 'All'}` : 
                        `${rule.FromPort || 'All'}-${rule.ToPort || 'All'}`;
                    
                    // Check if permissive (all ports or all protocols)
                    const isPermissive = rule.IpProtocol === '-1' || !rule.FromPort || portRange === 'All';
                    if (isPermissive) {
                        nodeMap.get(sg.GroupId).hasPermissiveRules = true;
                    }
                    
                    // SG-to-SG rules
                    if (rule.UserIdGroupPairs) {
                        rule.UserIdGroupPairs.forEach(pair => {
                            if (nodeMap.has(pair.GroupId)) {
                                links.push({
                                    source: pair.GroupId,
                                    target: sg.GroupId,
                                    protocol: protocol,
                                    ports: portRange,
                                    type: 'sg-to-sg',
                                    direction: 'ingress',
                                    isPermissive: isPermissive
                                });
                            }
                        });
                    }
                    
                    // Internet-exposed rules
                    if (rule.IpRanges) {
                        rule.IpRanges.forEach(ipRange => {
                            if (ipRange.CidrIp === '0.0.0.0/0') {
                                nodeMap.get(sg.GroupId).hasInternetAccess = true;
                                links.push({
                                    source: 'internet',
                                    target: sg.GroupId,
                                    protocol: protocol,
                                    ports: portRange,
                                    type: 'internet',
                                    direction: 'ingress',
                                    cidr: '0.0.0.0/0',
                                    isPermissive: isPermissive
                                });
                            }
                            // Note: Non-internet CIDR blocks are not visualized in the graph
                            // as they don't have corresponding nodes. Use the table below for full details.
                        });
                    }
                });
            }
            
            // Process egress rules
            if (sg.IpPermissionsEgress) {
                sg.IpPermissionsEgress.forEach(rule => {
                    const protocol = rule.IpProtocol === '-1' ? 'All' : rule.IpProtocol.toUpperCase();
                    const portRange = rule.FromPort === rule.ToPort ? 
                        `${rule.FromPort || 'All'}` : 
                        `${rule.FromPort || 'All'}-${rule.ToPort || 'All'}`;
                    
                    const isPermissive = rule.IpProtocol === '-1' || !rule.FromPort || portRange === 'All';
                    if (isPermissive) {
                        nodeMap.get(sg.GroupId).hasPermissiveRules = true;
                    }
                    
                    // SG-to-SG egress rules
                    if (rule.UserIdGroupPairs) {
                        rule.UserIdGroupPairs.forEach(pair => {
                            if (nodeMap.has(pair.GroupId)) {
                                links.push({
                                    source: sg.GroupId,
                                    target: pair.GroupId,
                                    protocol: protocol,
                                    ports: portRange,
                                    type: 'sg-to-sg',
                                    direction: 'egress',
                                    isPermissive: isPermissive
                                });
                            }
                        });
                    }
                    
                    // Prefix List egress rules (VPC Endpoints)
                    if (rule.PrefixListIds) {
                        rule.PrefixListIds.forEach(pl => {
                            const plId = pl.PrefixListId || pl;
                            const plDescription = pl.Description || pl.PrefixListName || '';
                            links.push({
                                source: sg.GroupId,
                                target: plId,
                                protocol: protocol,
                                ports: portRange,
                                type: 'prefix-list',
                                direction: 'egress',
                                isPermissive: isPermissive,
                                plDescription: plDescription  // Store description for later use
                            });
                        });
                    }
                });
            }
        });
        
        console.log('Created nodes:', nodes.length);
        console.log('Created links:', links.length);
        console.log('Sample node:', nodes[0]);
        console.log('Sample link:', links[0]);
        
        // Add internet node if needed
        if (links.some(l => l.source === 'internet')) {
            nodes.unshift({
                id: 'internet',
                name: 'Internet',
                isSpecial: true,
                hasInternetAccess: true
            });
            console.log('Added internet node');
        }
        
        // Add prefix list nodes (VPC Endpoints)
        const prefixListMap = new Map();  // Map of plId -> description
        links.forEach(l => {
            if (l.type === 'prefix-list') {
                if (!prefixListMap.has(l.target)) {
                    prefixListMap.set(l.target, l.plDescription || '');
                }
            }
        });
        
        prefixListMap.forEach((description, plId) => {
            // Extract service name from description
            // Format: "DynamoDB Gateway Egress" → "DynamoDB Endpoint"
            // or "S3 Gateway Egress" → "S3 Endpoint"
            // or strip "com.amazonaws.eu-west-1." prefix if present
            let serviceName = description;
            if (serviceName) {
                // Remove AWS region prefix like "com.amazonaws.eu-west-1."
                serviceName = serviceName.replace(/com\\.amazonaws\\.[a-z0-9-]+\\./g, '');
                // If it ends with "Gateway Egress" or similar, convert to "Service Endpoint"
                serviceName = serviceName.replace(/\\s*(Gateway\\s*)?(Egress|Ingress)/gi, '').trim();
                if (serviceName && !serviceName.toLowerCase().includes('endpoint')) {
                    serviceName = serviceName + ' Endpoint';
                }
            }
            if (!serviceName) {
                serviceName = plId;  // Fallback to ID if no description
            }
            
            nodes.push({
                id: plId,
                name: serviceName,
                originalDescription: description,  // Keep original for reference
                isPrefixList: true,
                isSpecial: true,
                totalRules: 0
            });
        });
        
        if (prefixListMap.size > 0) {
            console.log('Added prefix list nodes:', prefixListMap.size);
        }
        
        console.log('Starting D3 visualization...');
        
        // Create SVG
        const svg = d3.select('#sg-network-graph')
            .append('svg')
            .attr('width', width)
            .attr('height', height)
            .attr('viewBox', [0, 0, width, height]);
        
        // Add arrow markers for egress links
        const defs = svg.append('defs');
        
        // Blue arrow for SG-to-SG egress
        defs.append('marker')
            .attr('id', 'arrowhead-blue')
            .attr('viewBox', '-0 -3 6 6')
            .attr('refX', 18)
            .attr('refY', 0)
            .attr('orient', 'auto')
            .attr('markerWidth', 5)
            .attr('markerHeight', 5)
            .append('svg:path')
            .attr('d', 'M 0,-3 L 6,0 L 0,3')
            .attr('fill', '#4e8ac9');
        
        // Purple arrow for prefix list egress
        defs.append('marker')
            .attr('id', 'arrowhead-purple')
            .attr('viewBox', '-0 -3 6 6')
            .attr('refX', 18)
            .attr('refY', 0)
            .attr('orient', 'auto')
            .attr('markerWidth', 5)
            .attr('markerHeight', 5)
            .append('svg:path')
            .attr('d', 'M 0,-3 L 6,0 L 0,3')
            .attr('fill', '#9b59b6');
        
        console.log('SVG created');
        
        // Add zoom behavior
        const g = svg.append('g');
        svg.call(d3.zoom()
            .scaleExtent([0.1, 4])
            .on('zoom', (event) => g.attr('transform', event.transform)));
        
        // Create tooltip
        const tooltip = d3.select('body').append('div')
            .attr('class', 'sg-tooltip')
            .style('opacity', 0);
        
        // Create force simulation
        const simulation = d3.forceSimulation(nodes)
            .force('link', d3.forceLink(links).id(d => d.id).distance(150))
            .force('charge', d3.forceManyBody().strength(-300))
            .force('center', d3.forceCenter(width / 2, height / 2))
            .force('collision', d3.forceCollide().radius(40));
        
        // Draw links
        const link = g.append('g')
            .selectAll('line')
            .data(links)
            .join('line')
            .attr('class', d => d.isPermissive ? 'sg-link permissive' : 'sg-link')
            .attr('stroke', d => {
                if (d.type === 'internet') return '#dc3545';
                if (d.type === 'prefix-list') return '#9b59b6';  // Purple for VPC endpoints
                if (d.type === 'cidr') return '#ffc107';
                if (d.direction === 'egress') return '#4e8ac9';  // Blue for egress
                return '#28a745';  // Green for ingress
            })
            .attr('stroke-width', d => d.isPermissive ? 4 : 2)
            .attr('marker-end', d => d.direction === 'egress' ? 'url(#arrowhead-' + (d.type === 'prefix-list' ? 'purple' : 'blue') + ')' : '')
            .on('mouseover', function(event, d) {
                tooltip.transition().duration(200).style('opacity', 0.9);
                tooltip.html(`
                    <strong>Connection:</strong><br>
                    From: ${typeof d.source === 'object' ? d.source.name : d.source}<br>
                    To: ${typeof d.target === 'object' ? d.target.name : d.target}<br>
                    ${d.type === 'prefix-list' ? '<span style="color:#9b59b6;font-weight:bold;">🔷 VPC Endpoint</span><br>' : ''}
                    Direction: ${d.direction}<br>
                    Protocol: ${d.protocol}<br>
                    Ports: ${d.ports}<br>
                    ${d.isPermissive ? '<span style="color:#ff6b6b;font-weight:bold;">⚠️ ALL PORTS/PROTOCOLS</span><br>' : ''}
                    ${d.cidr ? 'CIDR: ' + d.cidr : ''}
                `)
                    .style('left', (event.pageX + 10) + 'px')
                    .style('top', (event.pageY - 28) + 'px');
            })
            .on('mouseout', function() {
                tooltip.transition().duration(500).style('opacity', 0);
            });
        
        // Draw nodes
        const node = g.append('g')
            .selectAll('g')
            .data(nodes)
            .join('g')
            .attr('class', 'sg-node')
            .call(d3.drag()
                .on('start', dragstarted)
                .on('drag', dragged)
                .on('end', dragended))
            .on('click', function(event, d) {
                // Highlight connected nodes
                const connectedIds = new Set();
                connectedIds.add(d.id);
                links.forEach(l => {
                    const sourceId = typeof l.source === 'object' ? l.source.id : l.source;
                    const targetId = typeof l.target === 'object' ? l.target.id : l.target;
                    if (sourceId === d.id) connectedIds.add(targetId);
                    if (targetId === d.id) connectedIds.add(sourceId);
                });
                
                node.classed('faded', n => !connectedIds.has(n.id));
                link.classed('faded', l => {
                    const sourceId = typeof l.source === 'object' ? l.source.id : l.source;
                    const targetId = typeof l.target === 'object' ? l.target.id : l.target;
                    return sourceId !== d.id && targetId !== d.id;
                });
            });
        
        // Add shapes based on node type
        node.each(function(d) {
            const g = d3.select(this);
            
            if (d.isPrefixList) {
                // Hexagon for VPC Endpoints
                const size = 25;
                const points = [];
                for (let i = 0; i < 6; i++) {
                    const angle = (Math.PI / 3) * i - Math.PI / 6;
                    points.push([
                        size * Math.cos(angle),
                        size * Math.sin(angle)
                    ]);
                }
                g.append('polygon')
                    .attr('points', points.map(p => p.join(',')).join(' '))
                    .attr('fill', '#9b59b6')  // Purple
                    .attr('stroke', '#fff')
                    .attr('stroke-width', 2);
            } else {
                // Circle for Security Groups and Internet
                g.append('circle')
                    .attr('r', d.isSpecial ? 25 : Math.min(30, 10 + (d.totalRules || 0)))
                    .attr('fill', () => {
                        if (d.id === 'internet') return '#dc3545';
                        if (d.hasInternetAccess) return '#ff6b6b';
                        return '#4e8ac9';
                    })
                    .attr('stroke', d.hasPermissiveRules ? '#ff0000' : '#fff')
                    .attr('stroke-width', d.hasPermissiveRules ? 3 : 2);
            }
        });
        
        node.append('text')
            .text(d => d.name.length > 15 ? d.name.substring(0, 12) + '...' : d.name)
            .attr('dy', d => d.isSpecial ? 35 : 30)
            .style('font-size', d => d.isSpecial ? '12px' : '10px')
            .style('font-weight', d => d.isSpecial ? 'bold' : 'normal');
        
        node.on('mouseover', function(event, d) {
            tooltip.transition().duration(200).style('opacity', 0.9);
            
            if (d.isPrefixList) {
                // VPC Endpoint tooltip
                const connections = links.filter(l => 
                    (typeof l.target === 'object' ? l.target.id : l.target) === d.id ||
                    (typeof l.source === 'object' ? l.source.id : l.source) === d.id
                );
                const sources = new Set();
                connections.forEach(l => {
                    const sourceId = typeof l.source === 'object' ? l.source.id : l.source;
                    const sourceName = typeof l.source === 'object' ? l.source.name : l.source;
                    if (sourceId !== d.id) sources.add(sourceName);
                });
                
                // Build bulleted source list
                const sourceList = Array.from(sources).map(s => `• ${s}`).join('<br>');
                
                tooltip.html(`
                    <strong>${d.name}</strong><br>
                    <strong>Prefix List:</strong> ${d.id}<br>
                    <strong>Connections:</strong> ${connections.length}<br>
                    <strong>Sources:</strong><br>${sourceList || '• None'}
                `);
            } else if (!d.isSpecial) {
                // Security Group tooltip
                tooltip.html(`
                    <strong>${d.name}</strong><br>
                    ID: ${d.id}<br>
                    VPC: ${d.vpcId || 'N/A'}<br>
                    Ingress Rules: ${d.ingressCount}<br>
                    Egress Rules: ${d.egressCount}<br>
                    ${d.description ? 'Description: ' + d.description + '<br>' : ''}
                `);
            } else {
                return; // Skip Internet node
            }
            
            tooltip.style('left', (event.pageX + 10) + 'px')
                   .style('top', (event.pageY - 28) + 'px');
        })
        .on('mouseout', function() {
            tooltip.transition().duration(500).style('opacity', 0);
        });
        
        simulation.on('tick', () => {
            link
                .attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);
            
            node.attr('transform', d => `translate(${d.x},${d.y})`);
        });
        
        function dragstarted(event, d) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }
        
        function dragged(event, d) {
            d.fx = event.x;
            d.fy = event.y;
        }
        
        function dragended(event, d) {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }
        
        // Global functions for controls
        window.resetGraph = function() {
            node.classed('faded', false);
            link.classed('faded', false);
            const showIngress = document.getElementById('showIngress').checked;
            const showEgress = document.getElementById('showEgress').checked;
            link.style('display', d => {
                if (!showIngress && d.direction === 'ingress') {
                    return 'none';
                }
                if (!showEgress && d.direction === 'egress') {
                    return 'none';
                }
                return null;
            });
        };
        
        window.filterInternetExposed = function() {
            const exposedIds = new Set(nodes.filter(n => n.hasInternetAccess).map(n => n.id));
            node.classed('faded', n => !exposedIds.has(n.id) && !n.isSpecial);
            link.classed('faded', l => {
                const sourceId = typeof l.source === 'object' ? l.source.id : l.source;
                const targetId = typeof l.target === 'object' ? l.target.id : l.target;
                return !exposedIds.has(sourceId) && !exposedIds.has(targetId);
            });
        };
        
        window.filterPermissive = function() {
            const permissiveIds = new Set(nodes.filter(n => n.hasPermissiveRules).map(n => n.id));
            node.classed('faded', n => !permissiveIds.has(n.id) && !n.isSpecial);
            link.classed('faded', l => !l.isPermissive);
        };
        
        window.filterByPort = function() {
            const portInput = document.getElementById('portFilter').value.trim();
            if (!portInput) {
                resetGraph();
                return;
            }
            
            const ports = portInput.split(',').map(p => p.trim());
            link.classed('faded', l => {
                const linkPorts = l.ports.toString();
                return !ports.some(p => linkPorts.includes(p));
            });
            
            // Fade nodes that don't have matching links
            const visibleLinkIds = new Set();
            links.forEach(l => {
                const linkPorts = l.ports.toString();
                if (ports.some(p => linkPorts.includes(p))) {
                    const sourceId = typeof l.source === 'object' ? l.source.id : l.source;
                    const targetId = typeof l.target === 'object' ? l.target.id : l.target;
                    visibleLinkIds.add(sourceId);
                    visibleLinkIds.add(targetId);
                }
            });
            node.classed('faded', n => !visibleLinkIds.has(n.id));
        };
        
        window.toggleIngress = function() {
            const showIngress = document.getElementById('showIngress').checked;
            const showEgress = document.getElementById('showEgress').checked;
            link.style('display', d => {
                if (!showIngress && d.direction === 'ingress') {
                    return 'none';
                }
                if (!showEgress && d.direction === 'egress') {
                    return 'none';
                }
                return null;
            });
        };
        
        window.toggleEgress = function() {
            const showIngress = document.getElementById('showIngress').checked;
            const showEgress = document.getElementById('showEgress').checked;
            link.style('display', d => {
                if (!showIngress && d.direction === 'ingress') {
                    return 'none';
                }
                if (!showEgress && d.direction === 'egress') {
                    return 'none';
                }
                return null;
            });
        };
    }
</script>
'''
    else:
        # Show message when raw data isn't available
        html += '''
<div class="alert alert-warning">
    ℹ️ Network visualization not available. Raw security group data not found in collected data.
    <br>Ensure aws_build_review script has been run and includes SecurityGroups data.
</div>
'''
    
    # Count issues
    high_risk = sum(1 for sg in sg_data.get('checks', []) if sg.get('Severity') == 'HIGH')
    
    if high_risk > 0:
        html += f'<div class="alert alert-danger">⚠️ Found {high_risk} security group(s) with high-risk configurations (open to internet)</div>\n'
    
    html += '<table class="sg-table">\n'
    html += '<thead><tr><th>Security Group</th><th>Name</th><th>VPC</th><th>Ingress Rules</th><th>Egress Rules</th><th>Open to Internet</th><th>Severity</th></tr></thead>\n'
    html += '<tbody>\n'
    
    for idx, sg in enumerate(sg_data.get('checks', [])):
        severity = sg.get('Severity', 'INFO')
        badge_class = f'badge-{severity.lower()}'
        open_rules = sg.get('OpenToInternet', [])
        open_text = f"{len(open_rules)} rules" if open_rules else "None"
        
        ingress_count = sg.get('IngressRules', 0)
        egress_count = sg.get('EgressRules', 0)
        
        # Make rule counts clickable
        ingress_link = f'<a href="#" class="rule-count-link" onclick="toggleRules(\'sg-ingress-{idx}\'); return false;">{ingress_count} rules</a>' if ingress_count > 0 else '0'
        egress_link = f'<a href="#" class="rule-count-link" onclick="toggleRules(\'sg-egress-{idx}\'); return false;">{egress_count} rules</a>' if egress_count > 0 else '0'
        
        html += f'''<tr>
            <td><span class="code">{sg.get("SecurityGroup", "")}</span></td>
            <td>{sg.get("Name", "")}</td>
            <td><span class="code">{sg.get("VPC", "")}</span></td>
            <td class="compact-cell">{ingress_link}</td>
            <td class="compact-cell">{egress_link}</td>
            <td>{open_text}</td>
            <td><span class="badge {badge_class}">{severity}</span></td>
        </tr>\n'''
        
        # Add expandable row for ingress rules
        if ingress_count > 0:
            ingress_rules_html = ''
            ingress_details = sg.get('IngressRuleDetails', [])
            
            if ingress_details:
                # Sort rules by severity (CRITICAL → HIGH → MEDIUM → LOW → COMPLIANT)
                ingress_details_sorted = sort_rules_by_severity(ingress_details, 'ingress')
                
                # We have the actual rule details - use continuous numbering
                rule_counter = 1
                for rule_idx, rule in enumerate(ingress_details_sorted):
                    html_chunk, rule_counter = format_security_group_rule(rule, 'ingress', rule_counter)
                    ingress_rules_html += html_chunk
            else:
                # No details available
                ingress_rules_html = '''<div class="alert alert-info">
                    <strong>Note:</strong> Detailed rule analysis requires updated verification script (v2.1.1+). 
                    Please regenerate the verification JSON with the latest script to see full rule analysis.
                </div>'''
            
            html += f'''<tr id="sg-ingress-{idx}" class="rules-expanded-row" style="display:none;">
                <td colspan="7">
                    <div class="rules-details">
                        <h4>📥 Ingress Rules ({ingress_count})</h4>
                        {ingress_rules_html}
                    </div>
                </td>
            </tr>\n'''
        
        # Add expandable row for egress rules
        if egress_count > 0:
            egress_rules_html = ''
            egress_details = sg.get('EgressRuleDetails', [])
            
            if egress_details:
                # Sort rules by severity (CRITICAL → HIGH → MEDIUM → LOW → COMPLIANT)
                egress_details_sorted = sort_rules_by_severity(egress_details, 'egress')
                
                # We have the actual rule details - use continuous numbering
                rule_counter = 1
                for rule_idx, rule in enumerate(egress_details_sorted):
                    html_chunk, rule_counter = format_security_group_rule(rule, 'egress', rule_counter)
                    egress_rules_html += html_chunk
            else:
                # No details available
                egress_rules_html = '''<div class="alert alert-info">
                    <strong>Note:</strong> Detailed rule analysis requires updated verification script (v2.1.1+). 
                    Please regenerate the verification JSON with the latest script to see full rule analysis.
                </div>'''
            
            html += f'''<tr id="sg-egress-{idx}" class="rules-expanded-row" style="display:none;">
                <td colspan="7">
                    <div class="rules-details">
                        <h4>📤 Egress Rules ({egress_count})</h4>
                        {egress_rules_html}
                    </div>
                </td>
            </tr>\n'''
    
    html += '</tbody></table>\n</div>\n'
    return html


def generate_compute_section(compute_data):
    """Generate HTML for compute resources section"""
    if not compute_data:
        return ""
    
    html = '<div class="section">\n'
    html += '<h2>Compute Resources</h2>\n'
    
    # EC2 Instances
    if compute_data.get('ec2'):
        html += '<h3>EC2 Instances</h3>\n'
        html += '<table>\n'
        html += '<thead><tr><th>Instance ID</th><th>Type</th><th>State</th><th>VPC</th><th>Monitoring</th><th>Public IP</th></tr></thead>\n'
        html += '<tbody>\n'
        
        for instance in compute_data['ec2']:
            state = instance.get('State', '')
            badge = 'badge-success' if state == 'running' else 'badge-warning'
            has_public = '✓' if instance.get('PublicIP') else '✗'
            monitoring = instance.get('Monitoring', 'disabled')
            
            html += f'''<tr>
                <td><span class="code">{instance.get("InstanceId", "")}</span></td>
                <td>{instance.get("InstanceType", "")}</td>
                <td><span class="badge {badge}">{state}</span></td>
                <td><span class="code">{instance.get("VPC", "")}</span></td>
                <td>{monitoring}</td>
                <td>{has_public}</td>
            </tr>\n'''
        
        html += '</tbody></table>\n'
    
    # Lambda Functions
    if compute_data.get('lambda'):
        html += '<h3>Lambda Functions</h3>\n'
        html += '<table>\n'
        html += '<thead><tr><th>Function Name</th><th>Runtime</th><th>Memory (MB)</th><th>Timeout (s)</th><th>VPC</th></tr></thead>\n'
        html += '<tbody>\n'
        
        for func in compute_data['lambda']:
            in_vpc = '✓' if func.get('VPC') else '✗'
            
            html += f'''<tr>
                <td><span class="code">{func.get("FunctionName", "")}</span></td>
                <td>{func.get("Runtime", "")}</td>
                <td>{func.get("Memory", "")}</td>
                <td>{func.get("Timeout", "")}</td>
                <td>{in_vpc}</td>
            </tr>\n'''
        
        html += '</tbody></table>\n'
    
    html += '</div>\n'
    return html


def generate_database_section(db_data):
    """Generate HTML for database section"""
    if not db_data:
        return ""
    
    html = '<div class="section">\n'
    html += '<h2>Databases</h2>\n'
    
    # RDS
    if db_data.get('rds'):
        html += '<h3>RDS Instances</h3>\n'
        html += '<table>\n'
        html += '<thead><tr><th>Identifier</th><th>Engine</th><th>Instance Class</th><th>Multi-AZ</th><th>Encrypted</th><th>Public</th><th>Backup Days</th></tr></thead>\n'
        html += '<tbody>\n'
        
        for db in db_data['rds']:
            multi_az = '✓' if db.get('MultiAZ') else '✗'
            encrypted = '✓' if db.get('StorageEncrypted') else '✗'
            public = '✓' if db.get('PubliclyAccessible') else '✗'
            public_badge = 'badge-danger' if db.get('PubliclyAccessible') else 'badge-success'
            
            html += f'''<tr>
                <td><span class="code">{db.get("DBInstanceIdentifier", "")}</span></td>
                <td>{db.get("Engine", "")} {db.get("EngineVersion", "")}</td>
                <td>{db.get("InstanceClass", "")}</td>
                <td>{multi_az}</td>
                <td>{encrypted}</td>
                <td><span class="badge {public_badge}">{public}</span></td>
                <td>{db.get("BackupRetention", 0)}</td>
            </tr>\n'''
        
        html += '</tbody></table>\n'
    
    html += '</div>\n'
    return html


def analyze_bucket_risk_from_tags(tags):
    """
    Analyze bucket risk level based on Environment and Data Classification tags.
    
    Environment Tags:
    - Development/Integration: Non-production/development network segment (Lower risk)
    - Staging/Prep/Prod/Production: Production network segment with potential PII/PCI data (Higher risk)
    
    Data Classification Tags:
    - Internal: Available to anyone in organization, no confidential/restricted data (Low risk)
    - Confidential: May contain PII, restricted to authorized personnel (Medium-High risk)
    - Restricted: Highest level - PII (health/financial/religion/sexual orientation), PCI data, 
                 catastrophic damage potential (Critical risk)
    
    Returns dict with: is_production, data_classification, risk_level, risk_description
    """
    environment = None
    data_classification = None
    
    for tag in tags:
        key = tag.get('Key', '').lower()
        value = tag.get('Value', '').lower()
        
        if key == 'environment':
            environment = value
        elif key == 'dataclassification' or key == 'data classification':
            data_classification = value
    
    # Determine if production
    is_production = False
    environment_risk = "Unknown"
    if environment in ['development', 'dev', 'integration', 'int']:
        is_production = False
        environment_risk = "Non-Production"
    elif environment in ['staging', 'stage', 'prep', 'prod', 'production', 'prd']:
        is_production = True
        environment_risk = "Production"
    
    # Determine data classification risk
    data_risk_level = "Unknown"
    data_risk_desc = "No data classification tag found"
    
    if data_classification == 'internal':
        data_risk_level = "Low"
        data_risk_desc = "Internal data - available to organization members, no confidential/restricted data"
    elif data_classification == 'confidential':
        data_risk_level = "Medium-High"
        data_risk_desc = "Confidential data - may contain PII, restricted to authorized personnel only"
    elif data_classification == 'restricted':
        data_risk_level = "Critical"
        data_risk_desc = "Restricted data - contains highest level PII (health/financial/religion/sexual orientation), PCI data, catastrophic damage potential"
    
    # Calculate overall risk level
    if data_classification == 'restricted':
        overall_risk = "CRITICAL"
    elif data_classification == 'confidential' and is_production:
        overall_risk = "HIGH"
    elif data_classification == 'confidential' or is_production:
        overall_risk = "MEDIUM"
    elif data_classification == 'internal' and not is_production:
        overall_risk = "LOW"
    else:
        overall_risk = "MEDIUM"  # Default for unknown
    
    return {
        'is_production': is_production,
        'environment': environment_risk,
        'data_classification': data_classification if data_classification else "Not Tagged",
        'data_risk_level': data_risk_level,
        'data_risk_description': data_risk_desc,
        'overall_risk': overall_risk
    }


def generate_storage_section(storage_data):
    """Generate HTML for S3 storage section"""
    if not storage_data or 'checks' not in storage_data:
        return ""
    
    html = '<div class="section">\n'
    html += '<h2>S3 Storage</h2>\n'
    html += '<table class="s3-table">\n'
    html += '<thead><tr><th>Bucket Name</th><th>Region</th><th>Tags</th><th>Versioning</th><th>Encryption</th><th>Public Block</th><th>Logging</th><th>Security Score</th><th>Action</th></tr></thead>\n'
    html += '<tbody>\n'
    
    for idx, bucket in enumerate(storage_data['checks']):
        if bucket.get('Status') == 'Error':
            html += f'''<tr>
                <td><span class="code">{bucket.get("BucketName", "")}</span></td>
                <td colspan="8"><span class="badge badge-danger">Error: {bucket.get("Error", "")}</span></td>
            </tr>\n'''
            continue
            
        score = bucket.get('SecurityScore', 0)
        score_badge = 'badge-success' if score >= 4 else 'badge-warning' if score >= 3 else 'badge-danger'
        needs_remediation = bucket.get('NeedsRemediation', False)
        
        # Format tags
        tags = bucket.get('Tags', [])
        if tags:
            # Show first 3 tags
            tags_html = '<br>'.join([f'<small><strong>{tag.get("Key")}:</strong> {tag.get("Value")}</small>' for tag in tags[:3]])
            if len(tags) > 3:
                # Add expandable section for additional tags (only tags beyond first 3)
                additional_tags_html = '<br>'.join([f'<small><strong>{tag.get("Key")}:</strong> {tag.get("Value")}</small>' for tag in tags[3:]])
                tags_html += f'''<br><small><a href="#" class="tag-expand-link" onclick="toggleTags('tags-{idx}'); return false;">+{len(tags) - 3} more...</a></small>
                <div id="tags-{idx}" class="tags-expanded" style="display:none;">
                    {additional_tags_html}
                    <br><a href="#" class="tag-expand-link" onclick="toggleTags('tags-{idx}'); return false;">Show less</a>
                </div>'''
        else:
            tags_html = '<small><em>No tags</em></small>'
        
        # Analyze risk from tags
        risk_analysis = analyze_bucket_risk_from_tags(tags)
        risk_indicator = ""
        
        # Add visual risk indicator for CRITICAL or HIGH risk buckets
        if risk_analysis['overall_risk'] in ['CRITICAL', 'HIGH']:
            risk_emoji = "🚨" if risk_analysis['overall_risk'] == 'CRITICAL' else "⚠️"
            risk_indicator = f' <span style="color: #dc3545; font-weight: bold;" title="{risk_analysis["overall_risk"]} Risk: {risk_analysis["environment"]} + {risk_analysis["data_classification"]}">{risk_emoji}</span>'
        
        html += f'''<tr>
            <td class="compact-cell"><span class="code">{bucket.get("BucketName", "")}{risk_indicator}</span></td>
            <td class="compact-cell">{bucket.get("Region", "N/A")}</td>
            <td>{tags_html}</td>
            <td class="compact-cell">{bucket.get("Versioning", "Disabled")}</td>
            <td class="compact-cell">{bucket.get("Encryption", "Disabled")}</td>
            <td class="compact-cell">{bucket.get("PublicAccessBlock", "Not Configured")}</td>
            <td class="compact-cell">{bucket.get("Logging", "Disabled")}</td>
            <td class="compact-cell"><span class="badge {score_badge}">{score}/4</span></td>
            <td class="compact-cell">'''
        
        if needs_remediation:
            priority = bucket.get('Priority', 'MEDIUM')
            priority_badge = 'badge-danger' if priority == 'HIGH' else 'badge-warning'
            html += f'<span class="badge {priority_badge}">{priority} Priority</span><br>'
            html += f'<button class="remediation-btn" onclick="toggleRemediation(\'remediation-{idx}\')">View Remediation</button>'
        else:
            html += '<span class="badge badge-success">✓ Compliant</span>'
        
        html += '</td></tr>\n'
        
        # Add remediation details row if needed
        if needs_remediation:
            # Analyze risk from tags
            risk_analysis = analyze_bucket_risk_from_tags(tags)
            
            # Set risk badge color
            risk_badge_class = {
                'CRITICAL': 'badge-danger',
                'HIGH': 'badge-danger', 
                'MEDIUM': 'badge-warning',
                'LOW': 'badge-success'
            }.get(risk_analysis['overall_risk'], 'badge-warning')
            
            html += f'''<tr id="remediation-{idx}" class="remediation-row" style="display:none;">
                <td colspan="9">
                    <div class="remediation-details">
                        <h4>🔧 Remediation Required</h4>
                        
                        <div class="alert alert-info">
                            <h5 style="margin-top: 0;">📊 Risk Analysis from Tags</h5>
                            <p><strong>Overall Risk Level:</strong> <span class="badge {risk_badge_class}">{risk_analysis['overall_risk']}</span></p>
                            <p><strong>Environment:</strong> {risk_analysis['environment']} 
                               {'⚠️ <strong>Production system</strong> - may have access to production data, PII, or PCI data' if risk_analysis['is_production'] else '✓ Non-production/development network segment'}
                            </p>
                            <p><strong>Data Classification:</strong> {risk_analysis['data_classification']} ({risk_analysis['data_risk_level']} risk)</p>
                            <p style="margin-bottom: 0;"><em>{risk_analysis['data_risk_description']}</em></p>
                        </div>
                        
                        <div class="alert alert-warning">
                            <strong>Issue:</strong> {bucket.get("RemediationRequired", "")}
                        </div>
                        
                        <div class="priority-info">
                            <strong>Priority:</strong> <span class="badge {priority_badge}">{priority}</span><br>
                            <strong>Reason:</strong> {bucket.get("PriorityReason", "")}<br>
                            <strong>Cost Impact:</strong> {bucket.get("CostImpact", "Unknown")}
                        </div>
                        
                        <h4>Missing Controls</h4>
                        <ul>
                            {''.join([f'<li>{control}</li>' for control in bucket.get("MissingControls", [])])}
                        </ul>
                        
                        <h4>Detailed Remediation Steps</h4>
            '''
            
            for step in bucket.get('RemediationSteps', []):
                html += f'''
                        <div class="remediation-step">
                            <h5>🛡️ {step.get("control", "")}</h5>
                            <p><strong>Why this matters:</strong> {step.get("reason", "")}</p>
                            
                            <h6>AWS CLI Command:</h6>
                            <pre class="code-block">{step.get("remediation", "")}</pre>
                            
                            <h6>Terraform/OpenTofu:</h6>
                            <pre class="code-block">{step.get("terraform", "")}</pre>
                            
                            <div class="alert alert-info">
                                <strong>⚠️ Considerations:</strong> {step.get("considerations", "")}
                            </div>
                        </div>
                '''
            
            html += '''
                    </div>
                </td>
            </tr>\n'''
    
    html += '</tbody></table>\n</div>\n'
    return html


def generate_bedrock_section(bedrock_data):
    """Generate HTML for Amazon Bedrock section"""
    if not bedrock_data or 'checks' not in bedrock_data:
        return ""
    
    html = '<div class="section">\n'
    html += '<h2>🤖 Amazon Bedrock Security</h2>\n'
    
    checks = bedrock_data.get('checks', [])
    if not checks:
        return ""
    
    # Count issues
    critical = sum(1 for check in checks if check.get('Severity') == 'CRITICAL')
    high = sum(1 for check in checks if check.get('Severity') == 'HIGH')
    medium = sum(1 for check in checks if check.get('Severity') == 'MEDIUM')
    
    if critical > 0:
        html += f'<div class="alert alert-danger">🚨 Found {critical} CRITICAL Bedrock security issue(s)</div>\n'
    elif high > 0:
        html += f'<div class="alert alert-warning">⚠️ Found {high} HIGH priority Bedrock security issue(s)</div>\n'
    elif medium > 0:
        html += f'<div class="alert alert-warning">⚠️ Found {medium} MEDIUM priority Bedrock security issue(s)</div>\n'
    else:
        html += '<div class="alert alert-info">✓ Bedrock configurations reviewed</div>\n'
    
    html += '<table>\n'
    html += '<thead><tr><th>Resource</th><th>Status</th><th>Severity</th><th>Details</th><th>Recommendation</th></tr></thead>\n'
    html += '<tbody>\n'
    
    for check in checks:
        severity = check.get('Severity', 'INFO')
        badge_class = f'badge-{severity.lower()}'
        status = check.get('Status', 'Unknown')
        
        details = check.get('Details', check.get('Issue', ''))
        recommendation = check.get('Recommendation', '-')
        
        html += f'''<tr>
            <td><span class="code">{check.get("Resource", "")}</span></td>
            <td>{status}</td>
            <td><span class="badge {badge_class}">{severity}</span></td>
            <td>{details}</td>
            <td>{recommendation}</td>
        </tr>\n'''
    
    html += '</tbody></table>\n</div>\n'
    return html


def generate_sagemaker_endpoint_details(endpoint_data: dict, endpoint_config: dict) -> str:
    """Generate detailed drill-down for a SageMaker endpoint"""
    endpoint_name = endpoint_data.get('EndpointName', 'Unknown')
    
    # Extract all endpoint details
    endpoint_arn = endpoint_data.get('EndpointArn', 'N/A')
    endpoint_status = endpoint_data.get('EndpointStatus', 'Unknown')
    creation_time = str(endpoint_data.get('CreationTime', 'Unknown'))
    last_modified = str(endpoint_data.get('LastModifiedTime', 'Unknown'))
    
    # Data capture configuration
    data_capture = endpoint_data.get('DataCaptureConfig', {})
    data_capture_enabled = data_capture.get('EnableCapture', False)
    data_capture_s3 = data_capture.get('DestinationS3Uri', 'N/A') if data_capture_enabled else 'Not configured'
    capture_percentage = data_capture.get('InitialSamplingPercentage', 0) if data_capture_enabled else 0
    
    # Production variants
    production_variants = endpoint_data.get('ProductionVariants', [])
    
    # Endpoint config details
    config_name = endpoint_data.get('EndpointConfigName', 'Unknown')
    kms_key_id = endpoint_config.get('KmsKeyId', 'Not configured') if endpoint_config else 'Not configured'
    
    # Production variant details from config
    config_variants = endpoint_config.get('ProductionVariants', []) if endpoint_config else []
    
    # Tags
    tags = endpoint_data.get('Tags', [])
    
    # Build HTML
    html = f'''
    <div style="background-color: #f8f9fa; padding: 20px; margin: 10px 0; border-left: 4px solid #FF9900; border-radius: 4px;">
        <h4 style="margin-top: 0; color: #232f3e;">📋 Endpoint Configuration</h4>
        <table style="width: 100%; background-color: white; border-collapse: collapse; margin: 10px 0;">
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 8px; font-weight: 600; color: #546e7a; width: 200px;">Endpoint Name:</td>
                <td style="padding: 8px;"><span class="code">{endpoint_name}</span></td>
            </tr>
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 8px; font-weight: 600; color: #546e7a;">ARN:</td>
                <td style="padding: 8px;"><span class="code" style="font-size: 0.85em; word-break: break-all;">{endpoint_arn}</span></td>
            </tr>
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 8px; font-weight: 600; color: #546e7a;">Status:</td>
                <td style="padding: 8px;"><span class="badge {'badge-info' if endpoint_status == 'InService' else 'badge-warning'}">{endpoint_status}</span></td>
            </tr>
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 8px; font-weight: 600; color: #546e7a;">Created:</td>
                <td style="padding: 8px;">{creation_time}</td>
            </tr>
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 8px; font-weight: 600; color: #546e7a;">Last Modified:</td>
                <td style="padding: 8px;">{last_modified}</td>
            </tr>
            <tr>
                <td style="padding: 8px; font-weight: 600; color: #546e7a;">Endpoint Config:</td>
                <td style="padding: 8px;"><span class="code">{config_name}</span></td>
            </tr>
        </table>

        <h4 style="margin-top: 20px; color: #232f3e;">🔐 Encryption & Security</h4>
        <table style="width: 100%; background-color: white; border-collapse: collapse; margin: 10px 0;">
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 8px; font-weight: 600; color: #546e7a; width: 200px;">KMS Key:</td>
                <td style="padding: 8px;">
                    {f'<span class="code">{kms_key_id}</span>' if kms_key_id != 'Not configured' else '<span class="badge badge-medium">⚠️ No customer-managed encryption</span>'}
                </td>
            </tr>
            <tr>
                <td style="padding: 8px; font-weight: 600; color: #546e7a;">Security Recommendation:</td>
                <td style="padding: 8px;">
                    {'<span class="badge badge-info">✓ Using customer-managed KMS key</span>' if kms_key_id != 'Not configured' else '<span class="badge badge-medium">Use customer-managed KMS keys for data encryption at rest</span>'}
                </td>
            </tr>
        </table>

        <h4 style="margin-top: 20px; color: #232f3e;">📊 Data Capture Configuration</h4>
        <table style="width: 100%; background-color: white; border-collapse: collapse; margin: 10px 0;">
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 8px; font-weight: 600; color: #546e7a; width: 200px;">Data Capture Enabled:</td>
                <td style="padding: 8px;">
                    {f'<span class="badge badge-info">Yes</span>' if data_capture_enabled else '<span class="badge badge-low">No</span>'}
                </td>
            </tr>
'''
    
    if data_capture_enabled:
        html += f'''
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 8px; font-weight: 600; color: #546e7a;">Destination S3 URI:</td>
                <td style="padding: 8px;"><span class="code" style="font-size: 0.85em; word-break: break-all;">{data_capture_s3}</span></td>
            </tr>
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 8px; font-weight: 600; color: #546e7a;">Sampling Percentage:</td>
                <td style="padding: 8px;">{capture_percentage}%</td>
            </tr>
            <tr>
                <td colspan="2" style="padding: 8px;">
                    <div style="background-color: #fff3e0; padding: 12px; border-left: 4px solid #f57c00; margin-top: 8px;">
                        <strong style="color: #e65100;">⚠️ Data capture is enabled. Verify S3 bucket security:</strong>
                        <ul style="margin: 10px 0 0 20px; color: #e65100;">
                            <li>Ensure bucket encryption is enabled</li>
                            <li>Verify bucket policy restricts public access</li>
                            <li>Check lifecycle policies for data retention</li>
                            <li>Confirm access logging is enabled</li>
                        </ul>
                    </div>
                </td>
            </tr>
'''
    
    html += '''
        </table>
'''
    
    # Production Variants (Active)
    if production_variants:
        html += '''
        <h4 style="margin-top: 20px; color: #232f3e;">🚀 Production Variants (Active)</h4>
        <table style="width: 100%; background-color: white; border-collapse: collapse; margin: 10px 0;">
            <thead>
                <tr style="background-color: #546e7a;">
                    <th style="padding: 10px; color: white; text-align: left;">Variant Name</th>
                    <th style="padding: 10px; color: white; text-align: left;">Model Name</th>
                    <th style="padding: 10px; color: white; text-align: left;">Instance Type</th>
                    <th style="padding: 10px; color: white; text-align: left;">Instance Count</th>
                    <th style="padding: 10px; color: white; text-align: left;">Current Weight</th>
                </tr>
            </thead>
            <tbody>
        '''
        
        for variant in production_variants:
            variant_name = variant.get('VariantName', 'Unknown')
            model_name = variant.get('DeployedModelName', variant.get('ModelName', 'Unknown'))
            current_instance_count = variant.get('CurrentInstanceCount', 0)
            desired_instance_count = variant.get('DesiredInstanceCount', 0)
            current_weight = variant.get('CurrentWeight', 0)
            
            # Get instance type from config
            config_variant = next((v for v in config_variants if v.get('VariantName') == variant_name), {})
            instance_type = config_variant.get('InstanceType', 'Unknown')
            
            html += f'''
                <tr style="border-bottom: 1px solid #ddd;">
                    <td style="padding: 8px;"><span class="code">{variant_name}</span></td>
                    <td style="padding: 8px;"><span class="code">{model_name}</span></td>
                    <td style="padding: 8px;"><span class="code">{instance_type}</span></td>
                    <td style="padding: 8px;">{current_instance_count} {f'→ {desired_instance_count}' if current_instance_count != desired_instance_count else ''}</td>
                    <td style="padding: 8px;">{current_weight}</td>
                </tr>
            '''
        
        html += '''
            </tbody>
        </table>
        '''
    
    # Configuration variants detail
    if config_variants:
        html += '''
        <h4 style="margin-top: 20px; color: #232f3e;">⚙️ Endpoint Config - Production Variants</h4>
        '''
        
        for variant in config_variants:
            variant_name = variant.get('VariantName', 'Unknown')
            model_name = variant.get('ModelName', 'Unknown')
            instance_type = variant.get('InstanceType', 'Unknown')
            initial_instance_count = variant.get('InitialInstanceCount', 0)
            initial_weight = variant.get('InitialVariantWeight', 0)
            
            html += f'''
        <details style="margin: 10px 0; border: 1px solid #ddd; border-radius: 4px; padding: 10px;">
            <summary style="cursor: pointer; font-weight: bold; padding: 10px; background-color: #e8eaf6; border-radius: 4px;">📦 Variant: {variant_name}</summary>
            <div style="margin: 10px 0;">
                <table style="width: 100%; background-color: white; border-collapse: collapse;">
                    <tr style="border-bottom: 1px solid #ddd;">
                        <td style="padding: 8px; font-weight: 600; color: #546e7a; width: 200px;">Model Name:</td>
                        <td style="padding: 8px;"><span class="code">{model_name}</span></td>
                    </tr>
                    <tr style="border-bottom: 1px solid #ddd;">
                        <td style="padding: 8px; font-weight: 600; color: #546e7a;">Instance Type:</td>
                        <td style="padding: 8px;"><span class="code">{instance_type}</span></td>
                    </tr>
                    <tr style="border-bottom: 1px solid #ddd;">
                        <td style="padding: 8px; font-weight: 600; color: #546e7a;">Initial Instance Count:</td>
                        <td style="padding: 8px;">{initial_instance_count}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; font-weight: 600; color: #546e7a;">Initial Weight:</td>
                        <td style="padding: 8px;">{initial_weight}</td>
                    </tr>
            '''
            
            # Container definition if available
            container_def = variant.get('ContainerDefinition', {})
            if container_def:
                image = container_def.get('Image', 'N/A')
                model_data = container_def.get('ModelDataUrl', 'N/A')
                
                html += f'''
                    <tr style="border-bottom: 1px solid #ddd;">
                        <td style="padding: 8px; font-weight: 600; color: #546e7a;">Container Image:</td>
                        <td style="padding: 8px;"><span class="code" style="font-size: 0.8em; word-break: break-all;">{image}</span></td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; font-weight: 600; color: #546e7a;">Model Data URL:</td>
                        <td style="padding: 8px;"><span class="code" style="font-size: 0.8em; word-break: break-all;">{model_data}</span></td>
                    </tr>
                '''
            
            html += '''
                </table>
            </div>
        </details>
            '''
    
    # Tags
    if tags:
        html += '''
        <h4 style="margin-top: 20px; color: #232f3e;">🏷️ Tags</h4>
        <table style="width: 100%; background-color: white; border-collapse: collapse; margin: 10px 0;">
            <thead>
                <tr style="background-color: #546e7a;">
                    <th style="padding: 10px; color: white; text-align: left;">Key</th>
                    <th style="padding: 10px; color: white; text-align: left;">Value</th>
                </tr>
            </thead>
            <tbody>
        '''
        
        for tag in tags:
            key = tag.get('Key', '')
            value = tag.get('Value', '')
            html += f'''
                <tr style="border-bottom: 1px solid #ddd;">
                    <td style="padding: 8px;"><span class="code">{key}</span></td>
                    <td style="padding: 8px;">{value}</td>
                </tr>
            '''
        
        html += '''
            </tbody>
        </table>
        '''
    
    html += '''
    </div>
    '''
    
    return html


def generate_sagemaker_section(sagemaker_data):
    """Generate HTML for Amazon SageMaker section"""
    if not sagemaker_data or 'checks' not in sagemaker_data:
        return ""
    
    html = '<div class="section">\n'
    html += '<h2>🧠 Amazon SageMaker Security</h2>\n'
    
    checks = sagemaker_data.get('checks', [])
    if not checks:
        return ""
    
    # Count issues by severity
    critical = sum(1 for check in checks if check.get('Severity') == 'CRITICAL')
    high = sum(1 for check in checks if check.get('Severity') == 'HIGH')
    medium = sum(1 for check in checks if check.get('Severity') == 'MEDIUM')
    
    if critical > 0:
        html += f'<div class="alert alert-danger">🚨 Found {critical} CRITICAL SageMaker security issue(s) requiring immediate attention!</div>\n'
    elif high > 0:
        html += f'<div class="alert alert-warning">⚠️ Found {high} HIGH priority SageMaker security issue(s)</div>\n'
    elif medium > 0:
        html += f'<div class="alert alert-warning">⚠️ Found {medium} MEDIUM priority SageMaker security issue(s)</div>\n'
    else:
        html += '<div class="alert alert-info">✓ SageMaker configurations reviewed</div>\n'
    
    # Group checks by resource type
    notebooks = [c for c in checks if c.get('ResourceType') == 'NotebookInstance']
    domains = [c for c in checks if c.get('ResourceType') == 'SageMakerDomain']
    training_jobs = [c for c in checks if c.get('ResourceType') == 'TrainingJob']
    endpoints = [c for c in checks if c.get('ResourceType') == 'Endpoint']
    feature_groups = [c for c in checks if c.get('ResourceType') == 'FeatureGroup']
    other_checks = [c for c in checks if not c.get('ResourceType')]
    
    # Notebook Instances
    if notebooks:
        html += '<h3>📓 Notebook Instances</h3>\n'
        html += '<table>\n'
        html += '<thead><tr><th>Notebook</th><th>Internet Access</th><th>Root Access</th><th>VPC</th><th>Encryption</th><th>Severity</th><th>Recommendation</th></tr></thead>\n'
        html += '<tbody>\n'
        
        for notebook in notebooks:
            severity = notebook.get('Severity', 'INFO')
            badge_class = f'badge-{severity.lower()}'
            
            issues_list = notebook.get('Issues', [])
            issues_html = '<br>'.join(issues_list) if issues_list else 'Compliant'
            
            html += f'''<tr>
                <td><span class="code">{notebook.get("Resource", "").replace("Notebook: ", "")}</span></td>
                <td>{notebook.get("DirectInternetAccess", "-")}</td>
                <td>{notebook.get("RootAccess", "-")}</td>
                <td>{notebook.get("VPC", "-")}</td>
                <td>{notebook.get("Encrypted", "-")}</td>
                <td><span class="badge {badge_class}">{severity}</span></td>
                <td><small>{notebook.get("Recommendation", "-")}</small></td>
            </tr>\n'''
        
        html += '</tbody></table>\n'
    
    # SageMaker Domains (Studio)
    if domains:
        html += '<h3>🎨 SageMaker Studio Domains</h3>\n'
        html += '<table>\n'
        html += '<thead><tr><th>Domain</th><th>Auth Mode</th><th>Network Access</th><th>Severity</th><th>Issues</th><th>Recommendation</th></tr></thead>\n'
        html += '<tbody>\n'
        
        for domain in domains:
            severity = domain.get('Severity', 'INFO')
            badge_class = f'badge-{severity.lower()}'
            
            issues_list = domain.get('Issues', [])
            issues_html = '<br>'.join(issues_list) if issues_list else 'No issues'
            
            html += f'''<tr>
                <td><span class="code">{domain.get("Resource", "").replace("Domain: ", "")}</span></td>
                <td>{domain.get("AuthMode", "-")}</td>
                <td>{domain.get("NetworkAccess", "-")}</td>
                <td><span class="badge {badge_class}">{severity}</span></td>
                <td><small>{issues_html}</small></td>
                <td><small>{domain.get("Recommendation", "-")}</small></td>
            </tr>\n'''
        
        html += '</tbody></table>\n'
    
    # Training Jobs
    if training_jobs:
        html += '<h3>🏋️ Training Jobs (Last 20)</h3>\n'
        html += '<table>\n'
        html += '<thead><tr><th>Job Name</th><th>Network Isolation</th><th>VPC</th><th>Severity</th><th>Issues</th></tr></thead>\n'
        html += '<tbody>\n'
        
        for job in training_jobs:
            severity = job.get('Severity', 'INFO')
            badge_class = f'badge-{severity.lower()}'
            
            issues_list = job.get('Issues', [])
            issues_html = '<br>'.join(issues_list) if issues_list else 'No issues'
            
            html += f'''<tr>
                <td><span class="code">{job.get("Resource", "").replace("Training Job: ", "")}</span></td>
                <td>{"Yes" if job.get("NetworkIsolation") else "No"}</td>
                <td>{job.get("VPC", "-")}</td>
                <td><span class="badge {badge_class}">{severity}</span></td>
                <td><small>{issues_html}</small></td>
            </tr>\n'''
        
        html += '</tbody></table>\n'
    
    # Endpoints
    if endpoints:
        html += '<h3>🌐 Model Endpoints</h3>\n'
        html += '<table>\n'
        html += '<thead><tr><th>Endpoint</th><th>Severity</th><th>Issues</th><th>Recommendation</th></tr></thead>\n'
        html += '<tbody>\n'
        
        for endpoint in endpoints:
            severity = endpoint.get('Severity', 'INFO')
            badge_class = f'badge-{severity.lower()}'
            
            issues_list = endpoint.get('Issues', [])
            issues_html = '<br>'.join(issues_list) if issues_list else 'No issues'
            endpoint_name = endpoint.get("Resource", "").replace("Endpoint: ", "")
            
            html += f'''<tr onclick="this.nextElementSibling.style.display = this.nextElementSibling.style.display === 'none' ? 'table-row' : 'none';" style="cursor: pointer;">
                <td><span class="code">{endpoint_name}</span> <small style="color: #666;">▼ Click for details</small></td>
                <td><span class="badge {badge_class}">{severity}</span></td>
                <td><small>{issues_html}</small></td>
                <td><small>{endpoint.get("Recommendation", "-")}</small></td>
            </tr>\n'''
            
            # Detailed drill-down row
            endpoint_detail_data = endpoint.get('_endpoint_data', {})
            endpoint_config_data = endpoint.get('_endpoint_config', {})
            
            html += f'''<tr style="display: none; background-color: #f8f9fa;">
                <td colspan="4">
                    {generate_sagemaker_endpoint_details(endpoint_detail_data, endpoint_config_data)}
                </td>
            </tr>\n'''
        
        html += '</tbody></table>\n'
    
    # Feature Groups
    if feature_groups:
        html += '<h3>📊 Feature Store</h3>\n'
        html += '<table>\n'
        html += '<thead><tr><th>Feature Group</th><th>Severity</th><th>Issues</th><th>Recommendation</th></tr></thead>\n'
        html += '<tbody>\n'
        
        for fg in feature_groups:
            severity = fg.get('Severity', 'INFO')
            badge_class = f'badge-{severity.lower()}'
            
            issues_list = fg.get('Issues', [])
            issues_html = '<br>'.join(issues_list) if issues_list else 'No issues'
            
            html += f'''<tr>
                <td><span class="code">{fg.get("Resource", "").replace("Feature Group: ", "")}</span></td>
                <td><span class="badge {badge_class}">{severity}</span></td>
                <td><small>{issues_html}</small></td>
                <td><small>{fg.get("Recommendation", "-")}</small></td>
            </tr>\n'''
        
        html += '</tbody></table>\n'
    
    # Other checks
    if other_checks:
        html += '<h3>General</h3>\n'
        html += '<table>\n'
        html += '<thead><tr><th>Resource</th><th>Status</th><th>Severity</th><th>Details</th></tr></thead>\n'
        html += '<tbody>\n'
        
        for check in other_checks:
            severity = check.get('Severity', 'INFO')
            badge_class = f'badge-{severity.lower()}'
            
            html += f'''<tr>
                <td>{check.get("Resource", "")}</td>
                <td>{check.get("Status", "")}</td>
                <td><span class="badge {badge_class}">{severity}</span></td>
                <td>{check.get("Details", "")}</td>
            </tr>\n'''
        
        html += '</tbody></table>\n'
    
    html += '</div>\n'
    return html


def generate_iam_section(iam_data):
    """Generate HTML for IAM section with security analysis"""
    if not iam_data:
        return ""
    
    html = '<div class="section">\n'
    html += '<h2>🔐 IAM Security Analysis</h2>\n'
    
    checks = iam_data.get('checks', [])
    
    if not checks:
        # Fallback to old format if checks don't exist
        roles = iam_data.get('roles', [])
        users = iam_data.get('users', [])
        
        if roles:
            html += '<h3>IAM Roles</h3>\n'
            html += '<table>\n'
            html += '<thead><tr><th>Role Name</th><th>Path</th><th>Attached Policies</th><th>Inline Policies</th><th>Max Session Duration</th></tr></thead>\n'
            html += '<tbody>\n'
            
            for role in roles:
                role_name = role.get('RoleName', '')
                path = role.get('Path', '/')
                attached_count = role.get('AttachedPolicies', 0)
                inline_count = role.get('InlinePolicies', 0)
                max_session = role.get('MaxSessionDuration', 3600)
                max_session_hours = max_session / 3600
                
                html += f'''<tr>
                    <td><span class="code">{role_name}</span></td>
                    <td>{path}</td>
                    <td>{attached_count}</td>
                    <td>{inline_count}</td>
                    <td>{max_session_hours:.1f}h</td>
                </tr>\n'''
            
            html += '</tbody></table>\n'
        
        if users:
            html += '<h3>IAM Users</h3>\n'
            html += '<table>\n'
            html += '<thead><tr><th>User Name</th><th>Path</th><th>Created Date</th></tr></thead>\n'
            html += '<tbody>\n'
            
            for user in users:
                user_name = user.get('UserName', '')
                path = user.get('Path', '/')
                create_date = user.get('CreateDate', '')
                
                if create_date:
                    try:
                        from datetime import datetime
                        if isinstance(create_date, str):
                            date_obj = datetime.fromisoformat(create_date.replace('Z', '+00:00'))
                            create_date = date_obj.strftime('%Y-%m-%d')
                    except:
                        pass
                
                html += f'''<tr>
                    <td><span class="code">{user_name}</span></td>
                    <td>{path}</td>
                    <td>{create_date}</td>
                </tr>\n'''
            
            html += '</tbody></table>\n'
        
        html += '</div>\n'
        return html
    
    # New format with security checks
    # Count issues by severity
    critical = sum(1 for check in checks if check.get('Severity') == 'CRITICAL')
    high = sum(1 for check in checks if check.get('Severity') == 'HIGH')
    medium = sum(1 for check in checks if check.get('Severity') == 'MEDIUM')
    
    if critical > 0:
        html += f'<div class="alert alert-danger">🚨 Found {critical} CRITICAL IAM security issue(s) requiring immediate attention!</div>\n'
    elif high > 0:
        html += f'<div class="alert alert-warning">⚠️ Found {high} HIGH priority IAM security issue(s)</div>\n'
    elif medium > 0:
        html += f'<div class="alert alert-warning">⚠️ Found {medium} MEDIUM priority IAM security issue(s)</div>\n'
    else:
        html += '<div class="alert alert-info">✓ IAM roles reviewed - no critical violations detected</div>\n'
    
    # Separate IAM roles from other checks
    role_checks = [c for c in checks if c.get('ResourceType') == 'IAMRole']
    user_checks = [c for c in checks if c.get('ResourceType') == 'IAMUsers']
    other_checks = [c for c in checks if c.get('ResourceType') not in ['IAMRole', 'IAMUsers']]
    
    # IAM Roles with Issues
    if role_checks:
        html += '<h3>🎭 IAM Roles - Security Analysis</h3>\n'
        html += '<table>\n'
        html += '<thead><tr><th>Role</th><th>Severity</th><th>Attached Policies</th><th>Inline Policies</th><th>Security Issues</th><th>Recommendation</th></tr></thead>\n'
        html += '<tbody>\n'
        
        for check in role_checks:
            severity = check.get('Severity', 'INFO')
            badge_class = f'badge-{severity.lower()}'
            role_name = check.get('Resource', '').replace('Role: ', '')
            
            issues_list = check.get('Issues', [])
            issues_html = '<br>'.join(issues_list) if issues_list else 'No issues'
            
            attached = check.get('AttachedPolicies', 0)
            inline = check.get('InlinePolicies', 0)
            recommendation = check.get('Recommendation', '-')
            
            html += f'''<tr>
                <td><span class="code">{role_name}</span></td>
                <td><span class="badge {badge_class}">{severity}</span></td>
                <td>{attached}</td>
                <td>{inline}</td>
                <td><small>{issues_html}</small></td>
                <td><small>{recommendation}</small></td>
            </tr>\n'''
        
        html += '</tbody></table>\n'
    
    # IAM Users Check
    if user_checks:
        html += '<h3>👥 IAM Users</h3>\n'
        for check in user_checks:
            severity = check.get('Severity', 'INFO')
            badge_class = f'badge-{severity.lower()}'
            
            user_count = check.get('UserCount', 0)
            issues_list = check.get('Issues', [])
            issues_html = '<br>'.join(issues_list)
            recommendation = check.get('Recommendation', '')
            
            html += f'''<div class="alert alert-warning">
                <span class="badge {badge_class}">{severity}</span> <strong>{user_count} IAM User(s) Found</strong><br>
                {issues_html}<br>
                <strong>Recommendation:</strong> {recommendation}
            </div>\n'''
    
    # Other checks
    if other_checks:
        html += '<h3>Summary</h3>\n'
        html += '<table>\n'
        html += '<thead><tr><th>Resource</th><th>Status</th><th>Details</th></tr></thead>\n'
        html += '<tbody>\n'
        
        for check in other_checks:
            severity = check.get('Severity', 'INFO')
            badge_class = f'badge-{severity.lower()}'
            
            html += f'''<tr>
                <td>{check.get("Resource", "")}</td>
                <td><span class="badge {badge_class}">{check.get("Status", "")}</span></td>
                <td>{check.get("Details", "")}</td>
            </tr>\n'''
        
        html += '</tbody></table>\n'
    
    html += '</div>\n'
    return html


def generate_monitoring_section(monitoring_data):
    """Generate HTML for CloudWatch Monitoring section"""
    if not monitoring_data:
        return ""
    
    html = '<div class="section">\n'
    html += '<h2>📊 CloudWatch Monitoring</h2>\n'
    
    # CloudWatch Alarms
    alarms = monitoring_data.get('alarms', [])
    if alarms:
        html += '<h3>CloudWatch Alarms</h3>\n'
        html += '<table>\n'
        html += '<thead><tr><th>Alarm Name</th><th>Metric</th><th>Namespace</th><th>State</th><th>Actions Enabled</th><th>Alarm Actions</th></tr></thead>\n'
        html += '<tbody>\n'
        
        for alarm in alarms:
            alarm_name = alarm.get('AlarmName', '')
            metric_name = alarm.get('MetricName', '')
            namespace = alarm.get('Namespace', '')
            state = alarm.get('State', 'UNKNOWN')
            actions_enabled = alarm.get('ActionsEnabled', False)
            alarm_actions_count = alarm.get('AlarmActions', 0)
            
            # State badge
            state_badge = 'badge-success' if state == 'OK' else 'badge-danger' if state == 'ALARM' else 'badge-warning'
            actions_badge = 'badge-success' if actions_enabled else 'badge-warning'
            
            html += f'''<tr>
                <td><span class="code">{alarm_name}</span></td>
                <td>{metric_name}</td>
                <td>{namespace}</td>
                <td><span class="badge {state_badge}">{state}</span></td>
                <td><span class="badge {actions_badge}">{'Enabled' if actions_enabled else 'Disabled'}</span></td>
                <td>{alarm_actions_count}</td>
            </tr>\n'''
        
        html += '</tbody></table>\n'
    
    # Log Groups
    log_groups = monitoring_data.get('log_groups', [])
    if log_groups:
        html += '<h3>CloudWatch Log Groups</h3>\n'
        html += '<table>\n'
        html += '<thead><tr><th>Log Group Name</th><th>Retention Days</th><th>Stored Bytes</th></tr></thead>\n'
        html += '<tbody>\n'
        
        for log_group in log_groups:
            log_group_name = log_group.get('LogGroupName', '')
            retention = log_group.get('RetentionDays', 'Never Expire')
            stored_bytes = log_group.get('StoredBytes', 0)
            
            # Format bytes
            if stored_bytes > 1024*1024*1024:
                stored_display = f"{stored_bytes / (1024*1024*1024):.2f} GB"
            elif stored_bytes > 1024*1024:
                stored_display = f"{stored_bytes / (1024*1024):.2f} MB"
            elif stored_bytes > 1024:
                stored_display = f"{stored_bytes / 1024:.2f} KB"
            else:
                stored_display = f"{stored_bytes} bytes"
            
            # Retention badge
            retention_badge = 'badge-warning' if retention == 'Never Expire' else 'badge-success'
            
            html += f'''<tr>
                <td><span class="code">{log_group_name}</span></td>
                <td><span class="badge {retention_badge}">{retention}</span></td>
                <td>{stored_display}</td>
            </tr>\n'''
        
        html += '</tbody></table>\n'
    
    # If no data, show message
    if not alarms and not log_groups:
        html += '<p>No CloudWatch monitoring data available.</p>\n'
    
    html += '</div>\n'
    return html


def generate_cis_benchmark_section(cis_data):
    """Generate HTML for CIS AWS Foundations Benchmark section"""
    if not cis_data or 'checks' not in cis_data:
        return ""
    
    html = '<div class="section">\n'
    html += '<h2>📋 CIS AWS Foundations Benchmark</h2>\n'
    
    checks = cis_data.get('checks', [])
    if not checks:
        return ""
    
    # Count by severity
    critical = sum(1 for c in checks if c.get('Severity') == 'CRITICAL')
    high = sum(1 for c in checks if c.get('Severity') == 'HIGH')
    medium = sum(1 for c in checks if c.get('Severity') == 'MEDIUM')
    passed = sum(1 for c in checks if c.get('Status') == 'PASS')
    
    if critical > 0:
        html += f'<div class="alert alert-danger">🚨 {critical} CRITICAL CIS compliance failure(s) - immediate action required!</div>\n'
    elif high > 0:
        html += f'<div class="alert alert-warning">⚠️ {high} HIGH priority CIS compliance issue(s)</div>\n'
    elif medium > 0:
        html += f'<div class="alert alert-warning">⚠️ {medium} MEDIUM priority CIS compliance issue(s)</div>\n'
    
    if passed > 0:
        html += f'<div class="alert alert-info">✓ {passed} CIS check(s) passed</div>\n'
    
    html += '<table>\n'
    html += '<thead><tr><th>Benchmark ID</th><th>Resource</th><th>Status</th><th>Severity</th><th>Finding</th><th>Recommendation</th></tr></thead>\n'
    html += '<tbody>\n'
    
    for check in checks:
        benchmark_id = check.get('BenchmarkID', '')
        resource = check.get('Resource', '')
        status = check.get('Status', '')
        severity = check.get('Severity', 'INFO')
        finding = check.get('Finding', check.get('Details', ''))
        recommendation = check.get('Recommendation', '-')
        
        severity_badge = f'badge-{severity.lower()}'
        status_class = 'badge-success' if status == 'PASS' else 'badge-danger'
        
        html += f'''<tr>
            <td><span class="code">{benchmark_id}</span></td>
            <td>{resource}</td>
            <td><span class="badge {status_class}">{status}</span></td>
            <td><span class="badge {severity_badge}">{severity}</span></td>
            <td>{finding}</td>
            <td><small>{recommendation}</small></td>
        </tr>\n'''
    
    html += '</tbody></table>\n</div>\n'
    return html


def generate_html_report(verification_data):
    """Generate complete HTML report"""
    
    content = ""
    
    # Get raw collected data if available
    collected_data = verification_data.get('CollectedData', {})
    
    # Generate sections
    for section in verification_data.get('Sections', []):
        title = section.get('title', '')
        
        if 'VPC' in title:
            content += generate_vpc_section(section, collected_data)
        elif 'Security Group' in title:
            # Add raw security group data for network visualization
            # Data structure is: collected_data['SecurityGroups']['SecurityGroups']
            sg_raw = collected_data.get('SecurityGroups', {}).get('SecurityGroups', [])
            section['raw_data'] = {'SecurityGroups': sg_raw}
            content += generate_security_groups_section(section)
        elif 'Compute' in title:
            content += generate_compute_section(section)
        elif 'Database' in title:
            content += generate_database_section(section)
        elif 'Storage' in title:
            content += generate_storage_section(section)
        elif 'IAM' in title:
            content += generate_iam_section(section)
        elif 'Monitoring' in title:
            content += generate_monitoring_section(section)
        elif 'CIS' in title or 'Benchmark' in title:
            content += generate_cis_benchmark_section(section)
        elif 'Bedrock' in title:
            content += generate_bedrock_section(section)
        elif 'SageMaker' in title:
            content += generate_sagemaker_section(section)
    
    # Fill template
    html = HTML_TEMPLATE.format(
        account_id=verification_data.get('AccountId', 'Unknown'),
        region=verification_data.get('Region', 'Unknown'),
        timestamp=verification_data.get('CollectionTimestamp', 'Unknown'),
        content=content,
        report_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )
    
    return html


def main():
    parser = argparse.ArgumentParser(description='Generate HTML report from verification JSON')
    parser.add_argument('--input', required=True, help='Path to verification JSON file')
    parser.add_argument('--output', help='Output HTML file path', default='report.html')
    
    args = parser.parse_args()
    
    # Load verification data
    with open(args.input, 'r') as f:
        verification_data = json.load(f)
    
    # Generate HTML
    html = generate_html_report(verification_data)
    
    # Save HTML
    output_path = Path(args.output)
    with open(output_path, 'w') as f:
        f.write(html)
    
    print(f"HTML report generated: {output_path}")


if __name__ == '__main__':
    main()