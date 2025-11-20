#!/usr/bin/env python3
"""
AWS Build Review HTML Report Generator
Converts JSON verification reports into readable HTML format
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
            padding: 20px;
            background: #f9f9f9;
            border-radius: 6px;
            border-left: 4px solid #2c5aa0;
            overflow-x: auto;
            max-width: 100%;
        }}
        
        h2 {{
            color: #2c5aa0;
            font-size: 24px;
            margin-bottom: 15px;
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
        .s3-table th:nth-child(3), .s3-table td:nth-child(3) {{ width: 25%; font-size: 11px; }} /* Tags - INCREASED */
        .s3-table th:nth-child(4), .s3-table td:nth-child(4) {{ width: 8%; }}  /* Versioning */
        .s3-table th:nth-child(5), .s3-table td:nth-child(5) {{ width: 8%; }}  /* Encryption */
        .s3-table th:nth-child(6), .s3-table td:nth-child(6) {{ width: 10%; }} /* Public Block */
        .s3-table th:nth-child(7), .s3-table td:nth-child(7) {{ width: 7%; }}  /* Logging */
        .s3-table th:nth-child(8), .s3-table td:nth-child(8) {{ width: 9%; }}  /* Security Score */
        .s3-table th:nth-child(9), .s3-table td:nth-child(9) {{ width: 10%; }} /* Action */
        
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
            const link = event.target;
            if (tagsDiv) {{
                if (tagsDiv.style.display === 'none') {{
                    tagsDiv.style.display = 'block';
                    link.textContent = 'Show less';
                }} else {{
                    tagsDiv.style.display = 'none';
                    // Restore original text with count
                    const parent = tagsDiv.parentElement;
                    const allTags = parent.querySelectorAll('.tags-expanded small');
                    const visibleTags = parent.querySelectorAll('small:not(.tags-expanded small)').length;
                    link.textContent = '+' + (allTags.length - visibleTags) + ' more...';
                }}
            }}
        }}
    </script>
</body>
</html>
"""


def generate_vpc_section(vpc_data):
    """Generate HTML for VPC architecture section"""
    if not vpc_data or 'checks' not in vpc_data:
        return ""
    
    html = '<div class="section">\n'
    html += '<h2>VPC Architecture</h2>\n'
    
    for check in vpc_data.get('checks', []):
        if 'VPC' in check and 'Check' in check:
            html += f'<h3>VPC: <span class="code">{check["VPC"]}</span> - {check["Check"]}</h3>\n'
            html += '<table>\n<thead><tr>'
            
            # Get all keys except VPC and Check
            keys = [k for k in check.keys() if k not in ['VPC', 'Check']]
            for key in keys:
                html += f'<th>{key}</th>'
            
            html += '</tr></thead>\n<tbody><tr>'
            
            for key in keys:
                value = check[key]
                if isinstance(value, dict):
                    value = json.dumps(value, indent=2)
                elif isinstance(value, bool):
                    value = '✓' if value else '✗'
                html += f'<td>{value}</td>'
            
            html += '</tr></tbody></table>\n'
    
    html += '</div>\n'
    return html


def generate_security_groups_section(sg_data):
    """Generate HTML for security groups section"""
    if not sg_data or 'checks' not in sg_data:
        return ""
    
    html = '<div class="section">\n'
    html += '<h2>Security Groups</h2>\n'
    
    # Count issues
    high_risk = sum(1 for sg in sg_data.get('checks', []) if sg.get('Severity') == 'HIGH')
    
    if high_risk > 0:
        html += f'<div class="alert alert-danger">⚠️ Found {high_risk} security group(s) with high-risk configurations (open to internet)</div>\n'
    
    html += '<table>\n'
    html += '<thead><tr><th>Security Group</th><th>Name</th><th>VPC</th><th>Ingress Rules</th><th>Egress Rules</th><th>Open to Internet</th><th>Severity</th></tr></thead>\n'
    html += '<tbody>\n'
    
    for sg in sg_data.get('checks', []):
        severity = sg.get('Severity', 'INFO')
        badge_class = f'badge-{severity.lower()}'
        open_rules = sg.get('OpenToInternet', [])
        open_text = f"{len(open_rules)} rules" if open_rules else "None"
        
        html += f'''<tr>
            <td><span class="code">{sg.get("SecurityGroup", "")}</span></td>
            <td>{sg.get("Name", "")}</td>
            <td><span class="code">{sg.get("VPC", "")}</span></td>
            <td>{sg.get("IngressRules", 0)}</td>
            <td>{sg.get("EgressRules", 0)}</td>
            <td>{open_text}</td>
            <td><span class="badge {badge_class}">{severity}</span></td>
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
        
        html += f'''<tr>
            <td class="compact-cell"><span class="code">{bucket.get("BucketName", "")}</span></td>
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
            html += f'''<tr id="remediation-{idx}" class="remediation-row" style="display:none;">
                <td colspan="9">
                    <div class="remediation-details">
                        <h4>🔧 Remediation Required</h4>
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


def generate_html_report(verification_data):
    """Generate complete HTML report"""
    
    content = ""
    
    # Generate sections
    for section in verification_data.get('Sections', []):
        title = section.get('title', '')
        
        if 'VPC' in title:
            content += generate_vpc_section(section)
        elif 'Security Group' in title:
            content += generate_security_groups_section(section)
        elif 'Compute' in title:
            content += generate_compute_section(section)
        elif 'Database' in title:
            content += generate_database_section(section)
        elif 'Storage' in title:
            content += generate_storage_section(section)
    
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
