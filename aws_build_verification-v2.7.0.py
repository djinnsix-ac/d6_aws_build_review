#!/usr/bin/env python3
"""
AWS Build Review Verification Script
Version: 2.6.0
Compares collected AWS infrastructure against HLD/detailed design specifications

Changelog:
- v2.6.0: FEATURE - IAM custom policy security analysis (privilege escalation, wildcards, data exfiltration)
- v2.5.10: Moved DynamoDB into Databases section output (consolidated with RDS/OpenSearch)
- v2.5.9: Fixed DynamoDB encryption detection - AWS owned keys are encrypted by default
- v2.5.8: Added DynamoDB verification (encryption, PITR, deletion protection)
- v2.5.7: Added verify_databases() function for RDS and OpenSearch
- v2.5.5: Added OpenSearch verification, enhanced RDS details (endpoint, subnets, monitoring)
- v2.5.4: Added LoadBalancerName to ECS ServiceDetails by looking up target groups in load balancers
- v2.5.3: Added LoadBalancers field to ECS ServiceDetails for HTML report display
- v2.5.2: Count individual destinations in rules (match AWS console and graph visualization)
- v2.5.1: Include CollectedData in report output for HTML generator network visualization
- v2.5.0: Added full endpoint and endpoint config data to SageMaker checks for HTML drill-down
- v2.4.0: Added CIS AWS Foundations Benchmark verification
- v2.3.0: Enhanced security checks for SageMaker and Bedrock
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Tuple
from collections import defaultdict


class BuildVerifier:
    def __init__(self, collected_data_path: str, design_spec_path: str = None):
        """Initialize with collected AWS data and optional design specification"""
        with open(collected_data_path, 'r') as f:
            self.collected_data = json.load(f)
        
        self.design_spec = None
        if design_spec_path:
            with open(design_spec_path, 'r') as f:
                self.design_spec = json.load(f)
        
        self.findings = []
    
    def add_finding(self, category: str, severity: str, title: str, details: str):
        """Add a verification finding"""
        self.findings.append({
            'Category': category,
            'Severity': severity,
            'Title': title,
            'Details': details
        })
    
    def verify_vpc_architecture(self) -> Dict[str, Any]:
        """Verify VPC architecture against best practices and design specs"""
        results = {
            'title': 'VPC Architecture Verification',
            'checks': []
        }
        
        vpc_data = self.collected_data.get('VPC', {}).get('VPCs', [])
        
        for vpc in vpc_data:
            vpc_id = vpc.get('VpcId')
            
            # Check for internet gateway
            has_igw = len(vpc.get('InternetGateways', [])) > 0
            results['checks'].append({
                'VPC': vpc_id,
                'Check': 'Internet Gateway',
                'Status': 'Present' if has_igw else 'Missing',
                'Value': len(vpc.get('InternetGateways', []))
            })
            
            # Check for NAT gateways
            nat_gateways = vpc.get('NatGateways', [])
            active_nats = [ng for ng in nat_gateways if ng.get('State') == 'available']
            results['checks'].append({
                'VPC': vpc_id,
                'Check': 'NAT Gateways',
                'Status': 'Present' if active_nats else 'Missing',
                'Value': len(active_nats)
            })
            
            # Check subnet distribution
            subnets = vpc.get('Subnets', [])
            public_subnets = [s for s in subnets if s.get('MapPublicIpOnLaunch')]
            private_subnets = [s for s in subnets if not s.get('MapPublicIpOnLaunch')]
            
            # Group by AZ
            az_distribution = defaultdict(lambda: {'public': 0, 'private': 0})
            for subnet in subnets:
                az = subnet.get('AvailabilityZone')
                if subnet.get('MapPublicIpOnLaunch'):
                    az_distribution[az]['public'] += 1
                else:
                    az_distribution[az]['private'] += 1
            
            results['checks'].append({
                'VPC': vpc_id,
                'Check': 'Subnet Distribution',
                'PublicSubnets': len(public_subnets),
                'PrivateSubnets': len(private_subnets),
                'AZs': len(az_distribution),
                'Distribution': dict(az_distribution)
            })
            
            # Check for VPC Flow Logs (this would need CloudWatch Logs verification)
            results['checks'].append({
                'VPC': vpc_id,
                'Check': 'VPC Configuration',
                'CIDRBlock': vpc.get('CidrBlock'),
                'DHCPOptions': vpc.get('DhcpOptionsId'),
                'IsDefault': vpc.get('IsDefault')
            })
            
            # Check route tables
            route_tables = vpc.get('RouteTables', [])
            for rt in route_tables:
                rt_id = rt.get('RouteTableId')
                routes = rt.get('Routes', [])
                
                has_igw_route = any(r.get('GatewayId', '').startswith('igw-') for r in routes)
                has_nat_route = any(r.get('NatGatewayId') for r in routes)
                
                results['checks'].append({
                    'VPC': vpc_id,
                    'RouteTable': rt_id,
                    'Routes': len(routes),
                    'HasIGWRoute': has_igw_route,
                    'HasNATRoute': has_nat_route,
                    'Associations': len(rt.get('Associations', []))
                })
        
        return results
    
    def verify_security_groups(self) -> Dict[str, Any]:
        """Verify security group configurations with detailed per-rule analysis"""
        results = {
            'title': 'Security Group Verification',
            'checks': []
        }
        
        security_groups = self.collected_data.get('SecurityGroups', {}).get('SecurityGroups', [])
        
        for sg in security_groups:
            sg_id = sg.get('GroupId')
            sg_name = sg.get('GroupName')
            
            # Get full rule details for HTML report
            ingress_rules = sg.get('IpPermissions', [])
            egress_rules = sg.get('IpPermissionsEgress', [])
            
            # Count individual permission entries (like AWS console does)
            ingress_count = 0
            for rule in ingress_rules:
                ingress_count += len(rule.get('UserIdGroupPairs', []))
                ingress_count += len(rule.get('IpRanges', []))
                ingress_count += len(rule.get('Ipv6Ranges', []))
                ingress_count += len(rule.get('PrefixListIds', []))
                if ingress_count == 0:
                    ingress_count = 1
            
            egress_count = 0
            for rule in egress_rules:
                egress_count += len(rule.get('UserIdGroupPairs', []))
                egress_count += len(rule.get('IpRanges', []))
                egress_count += len(rule.get('Ipv6Ranges', []))
                egress_count += len(rule.get('PrefixListIds', []))
                if egress_count == 0:
                    egress_count = 1
            
            # Analyze ingress rules in detail
            detailed_ingress_rules = []
            open_to_internet_count = 0
            highest_severity = 'INFO'
            severity_order = {'HIGH': 3, 'MEDIUM': 2, 'INFO': 1}
            
            for idx, rule in enumerate(ingress_rules):
                protocol = rule.get('IpProtocol', '-1')
                from_port = rule.get('FromPort', 'All')
                to_port = rule.get('ToPort', 'All')
                
                # Handle protocol naming
                if protocol == '-1':
                    protocol_name = 'All'
                elif protocol == '6':
                    protocol_name = 'TCP'
                elif protocol == '17':
                    protocol_name = 'UDP'
                elif protocol == '1':
                    protocol_name = 'ICMP'
                else:
                    protocol_name = protocol
                
                # Analyze each IP range
                for ip_range in rule.get('IpRanges', []):
                    cidr = ip_range.get('CidrIp', '')
                    description = ip_range.get('Description', '')
                    
                    is_open_to_internet = cidr == '0.0.0.0/0'
                    
                    # Determine rule severity
                    if is_open_to_internet:
                        open_to_internet_count += 1
                        
                        # Classify by port and protocol
                        if from_port == to_port:
                            port = from_port
                            
                            # HIGH risk ports - remote access and databases
                            if port in [22, 3389, 3306, 5432, 1433, 27017, 6379, 9200, 5601]:
                                rule_severity = 'HIGH'
                                if port == 22:
                                    risk_reason = 'SSH open to internet - HIGH RISK! Use AWS SSM Session Manager instead'
                                elif port == 3389:
                                    risk_reason = 'RDP open to internet - high risk of brute force attacks'
                                elif port in [3306, 5432, 1433, 27017]:
                                    risk_reason = 'Database port open to internet - data exposure risk'
                                elif port in [6379, 9200, 5601]:
                                    risk_reason = 'Data store/search engine open to internet - unauthorized access risk'
                                else:
                                    risk_reason = 'Sensitive service open to internet'
                            
                            # MEDIUM risk ports - management and non-standard services
                            elif port in [8080, 8443, 9090, 9443, 5000, 8000, 8888, 10250, 10255]:
                                rule_severity = 'MEDIUM'
                                risk_reason = 'Management/application port open to internet - should be restricted'
                            
                            # INFO risk - standard web ports (acceptable for public web services)
                            elif port in [80, 443]:
                                rule_severity = 'INFO'
                                if port == 443:
                                    risk_reason = 'HTTPS open to internet (typical for web services or AWS SSM Session Manager)'
                                else:
                                    risk_reason = 'HTTP open to internet (typical for web services, consider redirecting to HTTPS)'
                            
                            # MEDIUM risk - all other specific ports
                            else:
                                rule_severity = 'MEDIUM'
                                risk_reason = f'Port {port} open to internet - verify if intended'
                        
                        # Protocol without specific port
                        elif protocol_name == 'All':
                            rule_severity = 'HIGH'
                            risk_reason = 'All protocols and ports open to internet - extremely permissive'
                        else:
                            rule_severity = 'MEDIUM'
                            risk_reason = f'Port range {from_port}-{to_port} open to internet'
                    else:
                        # Not open to internet - INFO level
                        rule_severity = 'INFO'
                        risk_reason = f'Restricted to {cidr}'
                    
                    # Track highest severity
                    if severity_order.get(rule_severity, 0) > severity_order.get(highest_severity, 0):
                        highest_severity = rule_severity
                    
                    # Build detailed rule information
                    rule_detail = {
                        'RuleNumber': idx + 1,
                        'Protocol': protocol_name,
                        'FromPort': from_port,
                        'ToPort': to_port,
                        'Source': cidr,
                        'Description': description,
                        'IsOpenToInternet': is_open_to_internet,
                        'Severity': rule_severity,
                        'RiskReason': risk_reason
                    }
                    
                    detailed_ingress_rules.append(rule_detail)
                
                # Also check IPv6 ranges
                for ipv6_range in rule.get('Ipv6Ranges', []):
                    cidr = ipv6_range.get('CidrIpv6', '')
                    description = ipv6_range.get('Description', '')
                    
                    is_open_to_internet = cidr == '::/0'
                    
                    if is_open_to_internet:
                        open_to_internet_count += 1
                        rule_severity = 'MEDIUM'
                        risk_reason = 'IPv6 open to internet'
                        
                        if severity_order.get(rule_severity, 0) > severity_order.get(highest_severity, 0):
                            highest_severity = rule_severity
                    else:
                        rule_severity = 'INFO'
                        risk_reason = f'Restricted to {cidr}'
                    
                    rule_detail = {
                        'RuleNumber': idx + 1,
                        'Protocol': protocol_name,
                        'FromPort': from_port,
                        'ToPort': to_port,
                        'Source': cidr,
                        'Description': description,
                        'IsOpenToInternet': is_open_to_internet,
                        'Severity': rule_severity,
                        'RiskReason': risk_reason,
                        'IPVersion': 'IPv6'
                    }
                    
                    detailed_ingress_rules.append(rule_detail)
                
                # Check security group references
                for sg_ref in rule.get('UserIdGroupPairs', []):
                    ref_sg_id = sg_ref.get('GroupId', '')
                    ref_description = sg_ref.get('Description', '')
                    
                    rule_detail = {
                        'RuleNumber': idx + 1,
                        'Protocol': protocol_name,
                        'FromPort': from_port,
                        'ToPort': to_port,
                        'Source': f'sg: {ref_sg_id}',
                        'Description': ref_description,
                        'IsOpenToInternet': False,
                        'Severity': 'INFO',
                        'RiskReason': 'Restricted to security group',
                        'SourceType': 'SecurityGroup'
                    }
                    
                    detailed_ingress_rules.append(rule_detail)
            
            results['checks'].append({
                'SecurityGroup': sg_id,
                'Name': sg_name,
                'VPC': sg.get('VpcId'),
                'IngressRules': ingress_count,
                'EgressRules': egress_count,
                'IngressRuleDetails': ingress_rules,  # Full rule details for HTML report
                'EgressRuleDetails': egress_rules,    # Full rule details for HTML report
                'DetailedIngressRules': detailed_ingress_rules,  # Per-rule analysis
                'OpenToInternetCount': open_to_internet_count,
                'Severity': highest_severity
            })
        
        return results
    
    def verify_compute_resources(self) -> Dict[str, Any]:
        """Verify EC2, Lambda, ECS, and EKS configurations"""
        results = {
            'title': 'Compute Resources Verification',
            'ec2': [],
            'lambda': [],
            'ecs': [],
            'eks': []
        }
        
        # EC2 Instances
        instances = self.collected_data.get('EC2', {}).get('Instances', [])
        for instance in instances:
            instance_id = instance.get('InstanceId')
            results['ec2'].append({
                'InstanceId': instance_id,
                'InstanceType': instance.get('InstanceType'),
                'State': instance.get('State', {}).get('Name'),
                'VPC': instance.get('VpcId'),
                'Subnet': instance.get('SubnetId'),
                'SecurityGroups': [sg.get('GroupId') for sg in instance.get('SecurityGroups', [])],
                'IAMProfile': instance.get('IamInstanceProfile', {}).get('Arn'),
                'Monitoring': instance.get('Monitoring', {}).get('State'),
                'PublicIP': instance.get('PublicIpAddress')
            })
        
        # Lambda Functions
        functions = self.collected_data.get('Lambda', {}).get('Functions', [])
        for func_data in functions:
            func = func_data.get('Configuration', {}).get('Configuration', {})
            results['lambda'].append({
                'FunctionName': func.get('FunctionName'),
                'Runtime': func.get('Runtime'),
                'Memory': func.get('MemorySize'),
                'Timeout': func.get('Timeout'),
                'VPC': func.get('VpcConfig', {}).get('VpcId'),
                'Role': func.get('Role'),
                'Environment': 'HasVariables' if func.get('Environment', {}).get('Variables') else 'None'
            })
        
        # ECS Clusters
        ecs_clusters = self.collected_data.get('ECS', {}).get('Clusters', [])
        
        # Build target group to load balancer mapping
        tg_to_lb = {}
        load_balancers = self.collected_data.get('LoadBalancers', {}).get('LoadBalancers', [])
        for lb_data in load_balancers:
            lb = lb_data.get('LoadBalancer', {})
            lb_name = lb.get('LoadBalancerName')
            target_groups = lb_data.get('TargetGroups', [])
            for tg in target_groups:
                tg_arn = tg.get('TargetGroupArn', '')
                if tg_arn and lb_name:
                    tg_to_lb[tg_arn] = lb_name
        
        for cluster_data in ecs_clusters:
            cluster = cluster_data.get('Cluster', {})
            services = cluster_data.get('Services', [])
            
            service_details = []
            for svc in services:
                # Get load balancer name from target group ARN
                lb_name = None
                load_balancers_list = svc.get('loadBalancers', [])
                if load_balancers_list:
                    tg_arn = load_balancers_list[0].get('targetGroupArn', '')
                    lb_name = tg_to_lb.get(tg_arn)
                
                service_details.append({
                    'ServiceName': svc.get('serviceName'),
                    'Status': svc.get('status'),
                    'DesiredCount': svc.get('desiredCount'),
                    'RunningCount': svc.get('runningCount'),
                    'LaunchType': svc.get('launchType'),
                    'LoadBalancers': svc.get('loadBalancers', []),
                    'LoadBalancerName': lb_name
                })
            
            results['ecs'].append({
                'ClusterName': cluster.get('clusterName'),
                'Status': cluster.get('status'),
                'RegisteredInstances': cluster.get('registeredContainerInstancesCount'),
                'RunningTasks': cluster.get('runningTasksCount'),
                'Services': len(services),
                'ServiceDetails': service_details
            })
        
        # EKS Clusters
        eks_clusters = self.collected_data.get('EKS', {}).get('Clusters', [])
        for cluster_data in eks_clusters:
            cluster = cluster_data.get('Cluster', {})
            nodegroups = cluster_data.get('NodeGroups', [])
            
            results['eks'].append({
                'ClusterName': cluster.get('name'),
                'Version': cluster.get('version'),
                'Status': cluster.get('status'),
                'Endpoint': cluster.get('endpoint'),
                'VPC': cluster.get('resourcesVpcConfig', {}).get('vpcId'),
                'NodeGroups': len(nodegroups),
                'NodeGroupDetails': [
                    {
                        'NodeGroupName': ng.get('nodegroupName'),
                        'Status': ng.get('status'),
                        'InstanceTypes': ng.get('instanceTypes'),
                        'DesiredSize': ng.get('scalingConfig', {}).get('desiredSize')
                    }
                    for ng in nodegroups
                ]
            })
        
        return results
    
    def verify_databases(self) -> Dict[str, Any]:
        """Verify RDS, ElastiCache, OpenSearch, and DynamoDB configurations"""
        results = {
            'title': 'Database Verification',
            'rds': [],
            'elasticache': [],
            'opensearch': [],
            'dynamodb': {'checks': []}
        }
        
        # RDS Instances - Enhanced details
        db_instances = self.collected_data.get('RDS', {}).get('DBInstances', [])
        for db in db_instances:
            endpoint = db.get('Endpoint', {})
            subnet_group = db.get('DBSubnetGroup', {})
            
            results['rds'].append({
                'DBInstanceIdentifier': db.get('DBInstanceIdentifier'),
                'DBName': db.get('DBName'),
                'Engine': db.get('Engine'),
                'EngineVersion': db.get('EngineVersion'),
                'InstanceClass': db.get('DBInstanceClass'),
                'StorageType': db.get('StorageType'),
                'AllocatedStorage': db.get('AllocatedStorage'),
                'MaxAllocatedStorage': db.get('MaxAllocatedStorage'),
                'Iops': db.get('Iops'),
                'StorageThroughput': db.get('StorageThroughput'),
                'MultiAZ': db.get('MultiAZ'),
                'AvailabilityZone': db.get('AvailabilityZone'),
                'PubliclyAccessible': db.get('PubliclyAccessible'),
                'StorageEncrypted': db.get('StorageEncrypted'),
                'KmsKeyId': db.get('KmsKeyId'),
                'BackupRetention': db.get('BackupRetentionPeriod'),
                'PreferredBackupWindow': db.get('PreferredBackupWindow'),
                'PreferredMaintenanceWindow': db.get('PreferredMaintenanceWindow'),
                'LatestRestorableTime': str(db.get('LatestRestorableTime', '')),
                'DeletionProtection': db.get('DeletionProtection'),
                'IAMDatabaseAuthentication': db.get('IAMDatabaseAuthenticationEnabled'),
                'PerformanceInsightsEnabled': db.get('PerformanceInsightsEnabled'),
                'MonitoringInterval': db.get('MonitoringInterval'),
                'AutoMinorVersionUpgrade': db.get('AutoMinorVersionUpgrade'),
                'Endpoint': endpoint.get('Address', '') if endpoint else None,
                'Port': endpoint.get('Port') if endpoint else None,
                'VPC': subnet_group.get('VpcId') if subnet_group else None,
                'SubnetGroup': subnet_group.get('DBSubnetGroupName') if subnet_group else None,
                'Subnets': [s.get('SubnetIdentifier') for s in subnet_group.get('Subnets', [])] if subnet_group else [],
                'SecurityGroups': [sg.get('VpcSecurityGroupId') for sg in db.get('VpcSecurityGroups', [])]
            })
        
        # ElastiCache Clusters
        cache_clusters = self.collected_data.get('ElastiCache', {}).get('CacheClusters', [])
        for cluster in cache_clusters:
            results['elasticache'].append({
                'CacheClusterId': cluster.get('CacheClusterId'),
                'Engine': cluster.get('Engine'),
                'EngineVersion': cluster.get('EngineVersion'),
                'CacheNodeType': cluster.get('CacheNodeType'),
                'NumCacheNodes': cluster.get('NumCacheNodes'),
                'Status': cluster.get('CacheClusterStatus'),
                'SecurityGroups': [sg.get('SecurityGroupId') for sg in cluster.get('SecurityGroups', [])],
                'TransitEncryption': cluster.get('TransitEncryptionEnabled'),
                'AtRestEncryption': cluster.get('AtRestEncryptionEnabled')
            })
        
        # OpenSearch Domains
        opensearch_domains = self.collected_data.get('OpenSearch', {}).get('Domains', [])
        for domain in opensearch_domains:
            vpc_options = domain.get('VPCOptions', {})
            endpoint = domain.get('Endpoints', {})
            
            results['opensearch'].append({
                'DomainName': domain.get('DomainName'),
                'DomainId': domain.get('DomainId'),
                'ARN': domain.get('ARN'),
                'EngineVersion': domain.get('EngineVersion'),
                'Endpoint': endpoint.get('vpc') if endpoint else domain.get('Endpoint'),
                'Created': domain.get('Created'),
                'Deleted': domain.get('Deleted'),
                'Processing': domain.get('Processing'),
                'UpgradeProcessing': domain.get('UpgradeProcessing'),
                'InstanceType': domain.get('ClusterConfig', {}).get('InstanceType'),
                'InstanceCount': domain.get('ClusterConfig', {}).get('InstanceCount'),
                'DedicatedMasterEnabled': domain.get('ClusterConfig', {}).get('DedicatedMasterEnabled'),
                'ZoneAwarenessEnabled': domain.get('ClusterConfig', {}).get('ZoneAwarenessEnabled'),
                'VPCId': vpc_options.get('VPCId'),
                'SubnetIds': vpc_options.get('SubnetIds', []),
                'SecurityGroupIds': vpc_options.get('SecurityGroupIds', []),
                'AvailabilityZones': vpc_options.get('AvailabilityZones', []),
                'EncryptionAtRestEnabled': domain.get('EncryptionAtRestOptions', {}).get('Enabled'),
                'NodeToNodeEncryptionEnabled': domain.get('NodeToNodeEncryptionOptions', {}).get('Enabled'),
                'DomainEndpointOptions': domain.get('DomainEndpointOptions', {}),
                'AccessPolicies': domain.get('AccessPolicies'),
                'CognitoOptions': domain.get('CognitoOptions', {})
            })
        
        # DynamoDB Tables - Add to same results
        tables = self.collected_data.get('DynamoDB', {}).get('Tables', [])
        if tables:
            for table in tables:
                table_name = table.get('TableName', 'Unknown')
                table_status = table.get('TableStatus', 'Unknown')
                
                # Check encryption
                # Note: DynamoDB tables are ALWAYS encrypted at rest
                sse = table.get('SSEDescription', {})
                sse_status = sse.get('Status', '')
                
                if sse_status == 'ENABLED':
                    encryption_type = sse.get('SSEType', 'KMS')
                    encryption_enabled = True
                else:
                    encryption_type = 'AWS_OWNED'
                    encryption_enabled = True
                
                # Check PITR
                continuous_backups = table.get('ContinuousBackups', {})
                pitr_desc = continuous_backups.get('PointInTimeRecoveryDescription', {})
                pitr_enabled = pitr_desc.get('PointInTimeRecoveryStatus') == 'ENABLED'
                
                # Check deletion protection
                deletion_protected = table.get('DeletionProtectionEnabled', False)
                
                # Check billing mode
                billing = table.get('BillingModeSummary', {})
                billing_mode = billing.get('BillingMode', 'Unknown')
                
                # Get metrics
                item_count = table.get('ItemCount', 0)
                table_size = table.get('TableSizeBytes', 0)
                
                # Get tags
                tags = table.get('Tags', [])
                tag_dict = {tag.get('Key'): tag.get('Value') for tag in tags}
                
                # Determine issues and severity
                issues = []
                severity = 'INFO'
                
                if encryption_type == 'AWS_OWNED':
                    issues.append('Using AWS owned key - consider AWS managed or customer-managed KMS for auditability')
                    if severity == 'INFO':
                        severity = 'LOW'
                elif encryption_type == 'KMS':
                    kms_key = sse.get('KMSMasterKeyArn', '')
                    if 'aws/dynamodb' in kms_key.lower() or not kms_key:
                        issues.append('Using AWS managed key - consider customer-managed KMS for full control')
                        if severity == 'INFO':
                            severity = 'LOW'
                
                if not pitr_enabled:
                    issues.append('Point-in-time recovery disabled - cannot restore to specific timestamp')
                    if severity == 'INFO':
                        severity = 'MEDIUM'
                
                if not deletion_protected:
                    issues.append('No deletion protection - table can be accidentally deleted')
                    if severity == 'INFO':
                        severity = 'LOW'
                
                # Format size
                if table_size >= 1073741824:
                    size_display = f"{table_size / 1073741824:.2f} GB"
                elif table_size >= 1048576:
                    size_display = f"{table_size / 1048576:.2f} MB"
                elif table_size >= 1024:
                    size_display = f"{table_size / 1024:.2f} KB"
                else:
                    size_display = f"{table_size} bytes"
                
                results['dynamodb']['checks'].append({
                    'TableName': table_name,
                    'TableArn': table.get('TableArn', ''),
                    'Status': table_status,
                    'BillingMode': billing_mode,
                    'Encryption': encryption_type,
                    'EncryptionEnabled': encryption_enabled,
                    'KMSKeyId': sse.get('KMSMasterKeyArn', 'N/A') if encryption_type == 'KMS' else 'N/A',
                    'PITR': 'Enabled' if pitr_enabled else 'Disabled',
                    'PITREnabled': pitr_enabled,
                    'DeletionProtection': 'Yes' if deletion_protected else 'No',
                    'DeletionProtected': deletion_protected,
                    'ItemCount': item_count,
                    'TableSize': table_size,
                    'TableSizeDisplay': size_display,
                    'Tags': tag_dict,
                    'HasTags': len(tags) > 0,
                    'Issues': issues,
                    'Severity': severity
                })
        
        return results
    
    def verify_load_balancers(self) -> Dict[str, Any]:
        """Verify load balancer configurations"""
        results = {
            'title': 'Load Balancer Verification',
            'checks': []
        }
        
        load_balancers = self.collected_data.get('LoadBalancers', {}).get('LoadBalancers', [])
        
        for lb_data in load_balancers:
            lb = lb_data.get('LoadBalancer', {})
            listeners = lb_data.get('Listeners', [])
            target_groups = lb_data.get('TargetGroups', [])
            
            results['checks'].append({
                'LoadBalancerName': lb.get('LoadBalancerName'),
                'Type': lb.get('Type'),
                'Scheme': lb.get('Scheme'),
                'VPC': lb.get('VpcId'),
                'AvailabilityZones': [az.get('ZoneName') for az in lb.get('AvailabilityZones', [])],
                'SecurityGroups': lb.get('SecurityGroups', []),
                'Listeners': [
                    {
                        'Protocol': l.get('Protocol'),
                        'Port': l.get('Port'),
                        'SSLPolicy': l.get('SslPolicy')
                    }
                    for l in listeners
                ],
                'TargetGroups': [
                    {
                        'Name': tg.get('TargetGroupName'),
                        'Protocol': tg.get('Protocol'),
                        'Port': tg.get('Port'),
                        'HealthCheckEnabled': tg.get('HealthCheckEnabled'),
                        'HealthyTargets': len([t for t in tg.get('Targets', []) if t.get('TargetHealth', {}).get('State') == 'healthy']),
                        'TotalTargets': len(tg.get('Targets', []))
                    }
                    for tg in target_groups
                ]
            })
        
        return results
    
    def verify_storage(self) -> Dict[str, Any]:
        """Verify S3 bucket configurations"""
        results = {
            'title': 'S3 Storage Verification',
            'checks': []
        }
        
        buckets = self.collected_data.get('S3', {}).get('Buckets', [])
        
        for bucket in buckets:
            if 'Error' in bucket:
                results['checks'].append({
                    'BucketName': bucket.get('Name'),
                    'Status': 'Error',
                    'Error': bucket.get('Error')
                })
                continue
            
            bucket_name = bucket.get('Name')
            versioning_status = bucket.get('Versioning', {}).get('Status', 'Disabled')
            has_encryption = bucket.get('Encryption') is not None
            has_public_block = bucket.get('PublicAccessBlock') is not None
            has_logging = bucket.get('Logging', {}).get('LoggingEnabled') is not None
            
            # Get tags if available
            tags = []
            if bucket.get('Tagging') and bucket.get('Tagging').get('TagSet'):
                tags = bucket.get('Tagging').get('TagSet')
            
            # Calculate security score
            security_score = sum([
                versioning_status == 'Enabled',
                has_encryption,
                has_public_block,
                has_logging
            ])
            
            # Build bucket result
            bucket_result = {
                'BucketName': bucket_name,
                'Region': bucket.get('Location', {}).get('LocationConstraint'),
                'Versioning': versioning_status,
                'Encryption': 'Enabled' if has_encryption else 'Disabled',
                'PublicAccessBlock': 'Configured' if has_public_block else 'Not Configured',
                'Logging': 'Enabled' if has_logging else 'Disabled',
                'Tags': tags,
                'SecurityScore': security_score
            }
            
            # Add remediation information if score is less than 4
            if security_score < 4:
                missing_controls = []
                remediation_steps = []
                
                # Check what's missing and build remediation
                if versioning_status != 'Enabled':
                    missing_controls.append('Versioning')
                    remediation_steps.append({
                        'control': 'Versioning',
                        'reason': 'Versioning protects against accidental deletion and overwrites, allows recovery of previous object versions, and is required for compliance with many frameworks. It provides an audit trail of object changes.',
                        'remediation': f'aws s3api put-bucket-versioning --bucket {bucket_name} --versioning-configuration Status=Enabled',
                        'terraform': f'''resource "aws_s3_bucket_versioning" "{bucket_name.replace('-', '_')}_versioning" {{
  bucket = "{bucket_name}"
  versioning_configuration {{
    status = "Enabled"
  }}
}}''',
                        'considerations': 'Versioning will increase storage costs as it retains previous versions. Consider adding a lifecycle policy to expire old versions after 30-90 days to manage costs.'
                    })
                
                if not has_encryption:
                    missing_controls.append('Encryption')
                    remediation_steps.append({
                        'control': 'Encryption',
                        'reason': 'Encryption at rest protects data from unauthorized access if storage media is compromised. It is a fundamental security control and often required for compliance (GDPR, HIPAA, PCI-DSS).',
                        'remediation': f'aws s3api put-bucket-encryption --bucket {bucket_name} --server-side-encryption-configuration \'{{"Rules": [{{"ApplyServerSideEncryptionByDefault": {{"SSEAlgorithm": "AES256"}}}}]}}\'',
                        'terraform': f'''resource "aws_s3_bucket_server_side_encryption_configuration" "{bucket_name.replace('-', '_')}_encryption" {{
  bucket = "{bucket_name}"
  rule {{
    apply_server_side_encryption_by_default {{
      sse_algorithm = "AES256"
    }}
  }}
}}''',
                        'considerations': 'AES256 (SSE-S3) is AWS managed and has no additional cost. For enhanced control, consider using KMS encryption (SSE-KMS) with customer managed keys.'
                    })
                
                if not has_public_block:
                    missing_controls.append('Public Access Block')
                    remediation_steps.append({
                        'control': 'Public Access Block',
                        'reason': 'Public Access Block prevents accidental exposure of bucket contents to the internet. It provides defense-in-depth against misconfigurations in bucket policies or ACLs that could make data publicly accessible.',
                        'remediation': f'aws s3api put-public-access-block --bucket {bucket_name} --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"',
                        'terraform': f'''resource "aws_s3_bucket_public_access_block" "{bucket_name.replace('-', '_')}_public_block" {{
  bucket = "{bucket_name}"
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}}''',
                        'considerations': 'Ensure your applications do not require public access before enabling. Use CloudFront or pre-signed URLs for controlled public access if needed.'
                    })
                
                if not has_logging:
                    missing_controls.append('Access Logging')
                    remediation_steps.append({
                        'control': 'Access Logging',
                        'reason': 'Server access logging provides detailed records of all requests made to the bucket. This is essential for security auditing, forensic analysis, compliance reporting, and detecting unauthorized access attempts.',
                        'remediation': f'''# First, create or identify a logging bucket, then:
aws s3api put-bucket-logging --bucket {bucket_name} --bucket-logging-status '{{"LoggingEnabled": {{"TargetBucket": "YOUR-LOGGING-BUCKET", "TargetPrefix": "{bucket_name}/"}}}}' ''',
                        'terraform': f'''resource "aws_s3_bucket_logging" "{bucket_name.replace('-', '_')}_logging" {{
  bucket = "{bucket_name}"
  target_bucket = "YOUR-LOGGING-BUCKET"
  target_prefix = "{bucket_name}/"
}}''',
                        'considerations': 'You need a dedicated logging bucket with appropriate permissions. Logging data is typically <1% of bucket size. Consider log retention policies (e.g., 90-365 days) to manage storage costs.'
                    })
                
                bucket_result['NeedsRemediation'] = True
                bucket_result['MissingControls'] = missing_controls
                bucket_result['RemediationRequired'] = f"This bucket scores {security_score}/4 because it is missing {len(missing_controls)} security control(s): {', '.join(missing_controls)}. These controls are essential for protecting data integrity, confidentiality, and maintaining audit trails."
                bucket_result['RemediationSteps'] = remediation_steps
                
                # Add cost estimate
                if 'Versioning' in missing_controls or 'Access Logging' in missing_controls:
                    bucket_result['CostImpact'] = 'Low to Medium - Versioning and logging will increase storage costs. Consider lifecycle policies to manage retention.'
                else:
                    bucket_result['CostImpact'] = 'Negligible - Encryption and public access blocks have no additional cost.'
                
                # Add priority recommendation
                if not has_encryption or not has_public_block:
                    bucket_result['Priority'] = 'HIGH'
                    bucket_result['PriorityReason'] = 'Missing encryption or public access controls represents a significant security risk.'
                else:
                    bucket_result['Priority'] = 'MEDIUM'
                    bucket_result['PriorityReason'] = 'Missing versioning or logging reduces operational resilience and audit capability.'
            else:
                bucket_result['NeedsRemediation'] = False
                bucket_result['Status'] = 'All security controls properly configured'
            
            results['checks'].append(bucket_result)
        
        return results
    
    def _analyze_iam_policy_security(self, policy_document, policy_name, role_name=None):
        """
        Analyze IAM policy for security violations
        
        Checks for:
        - Wildcard (*) in Action with Resource: *
        - AdministratorAccess or overly permissive policies
        - Privilege escalation risks
        - Resource: * with sensitive actions
        - Missing conditions on powerful actions
        """
        issues = []
        severity = 'INFO'
        
        if not policy_document or 'Statement' not in policy_document:
            return {'issues': [], 'severity': 'INFO'}
        
        statements = policy_document.get('Statement', [])
        if not isinstance(statements, list):
            statements = [statements]
        
        for stmt_idx, statement in enumerate(statements):
            if statement.get('Effect') != 'Allow':
                continue  # Only check Allow statements
            
            actions = statement.get('Action', [])
            if isinstance(actions, str):
                actions = [actions]
            
            resources = statement.get('Resource', [])
            if isinstance(resources, str):
                resources = [resources]
            
            conditions = statement.get('Condition', {})
            
            # CRITICAL: Full admin access (Action: *, Resource: *)
            if '*' in actions and '*' in resources:
                issues.append("🚨 CRITICAL: Full admin access - Action: * with Resource: *")
                severity = 'CRITICAL'
                continue
            
            # HIGH: Wildcard action with wildcard resource
            has_wildcard_action = any('*' in action for action in actions)
            has_wildcard_resource = '*' in resources
            
            if has_wildcard_action and has_wildcard_resource:
                issues.append(f"⚠️ HIGH: Wildcard permissions - Action with wildcard on Resource: *")
                if severity not in ['CRITICAL']:
                    severity = 'HIGH'
            
            # HIGH: Sensitive actions with Resource: *
            sensitive_actions = [
                'iam:CreateUser', 'iam:CreateRole', 'iam:AttachUserPolicy', 
                'iam:AttachRolePolicy', 'iam:PutUserPolicy', 'iam:PutRolePolicy',
                'iam:CreateAccessKey', 'iam:UpdateAssumeRolePolicy',
                'sts:AssumeRole',
                'kms:Decrypt', 'kms:CreateGrant',
                'secretsmanager:GetSecretValue',
                's3:GetObject', 's3:PutObject', 's3:DeleteObject',
                'lambda:InvokeFunction', 'lambda:UpdateFunctionCode',
                'ec2:RunInstances', 'ec2:ModifyInstanceAttribute'
            ]
            
            for action in actions:
                # Check if action is in sensitive list or uses wildcard
                if action in sensitive_actions or ('*' in action and any(sens in action for sens in sensitive_actions)):
                    if '*' in resources and not conditions:
                        issues.append(f"⚠️ HIGH: Sensitive action '{action}' with Resource: * and no conditions")
                        if severity not in ['CRITICAL', 'HIGH']:
                            severity = 'HIGH'
            
            # HIGH: IAM privilege escalation risks
            iam_escalation_actions = [
                'iam:CreatePolicyVersion', 'iam:SetDefaultPolicyVersion',
                'iam:PassRole', 'iam:CreateAccessKey', 'iam:CreateLoginProfile',
                'iam:UpdateAssumeRolePolicy', 'iam:AttachUserPolicy', 'iam:AttachRolePolicy',
                'iam:PutUserPolicy', 'iam:PutRolePolicy', 'iam:AddUserToGroup',
                'iam:UpdateLoginProfile'
            ]
            
            escalation_found = [action for action in actions if action in iam_escalation_actions or (action == 'iam:*')]
            if escalation_found and ('*' in resources or not conditions):
                issues.append(f"⚠️ HIGH: Privilege escalation risk - {', '.join(escalation_found[:3])} without restrictions")
                if severity not in ['CRITICAL', 'HIGH']:
                    severity = 'HIGH'
            
            # MEDIUM: PassRole without conditions
            if 'iam:PassRole' in actions and not conditions:
                issues.append(f"⚠️ MEDIUM: iam:PassRole without conditions - can pass any role to any service")
                if severity not in ['CRITICAL', 'HIGH', 'MEDIUM']:
                    severity = 'MEDIUM'
            
            # MEDIUM: S3 full access
            if 's3:*' in actions and '*' in resources:
                issues.append(f"⚠️ MEDIUM: Full S3 access across all buckets")
                if severity not in ['CRITICAL', 'HIGH', 'MEDIUM']:
                    severity = 'MEDIUM'
            
            # MEDIUM: Lambda full access
            if 'lambda:*' in actions and '*' in resources:
                issues.append(f"⚠️ MEDIUM: Full Lambda access - can modify function code")
                if severity not in ['CRITICAL', 'HIGH', 'MEDIUM']:
                    severity = 'MEDIUM'
            
            # LOW: Broad service wildcards
            broad_wildcards = ['ec2:*', 'rds:*', 'dynamodb:*', 'sqs:*', 'sns:*']
            found_broad = [action for action in actions if action in broad_wildcards]
            if found_broad and '*' in resources:
                issues.append(f"ℹ️ LOW: Broad service permissions - {', '.join(found_broad[:2])}")
                if severity == 'INFO':
                    severity = 'LOW'
        
        return {'issues': issues, 'severity': severity}
    
    def _analyze_custom_policies(self, custom_policies):
        """
        Analyze customer-managed IAM policies for security issues
        Returns list of check results for each policy
        """
        policy_checks = []
        
        for policy_data in custom_policies:
            policy_meta = policy_data.get('PolicyMetadata', {})
            policy_doc = policy_data.get('PolicyDocument')
            policy_name = policy_meta.get('PolicyName', 'Unknown')
            policy_arn = policy_meta.get('Arn', '')
            
            # Skip if no policy document
            if not policy_doc:
                continue
            
            # Analyze the policy document
            analysis = self._analyze_iam_policy_security(policy_doc, policy_name)
            
            # Get additional metadata
            statement_count = len(policy_doc.get('Statement', []))
            policy_size = len(json.dumps(policy_doc))
            
            # Check for wildcards
            has_wildcard_actions = self._check_wildcard_actions(policy_doc)
            has_wildcard_resources = self._check_wildcard_resources(policy_doc)
            has_conditions = self._check_has_conditions(policy_doc)
            
            # Extract high-risk actions
            high_risk_actions = self._extract_high_risk_actions(policy_doc)
            
            # Build detailed issues list with categories
            detailed_issues = []
            for issue in analysis['issues']:
                # Categorize issues
                if 'CRITICAL' in issue:
                    category = 'Privilege Escalation' if 'admin' in issue.lower() else 'Critical Security Risk'
                elif 'escalation' in issue.lower():
                    category = 'Privilege Escalation'
                elif 'wildcard' in issue.lower() or 'Resource: *' in issue:
                    category = 'Overly Permissive'
                elif 's3:' in issue.lower():
                    category = 'Data Exfiltration Risk'
                elif 'PassRole' in issue:
                    category = 'Privilege Escalation'
                else:
                    category = 'Best Practice Violation'
                
                detailed_issues.append({
                    'Category': category,
                    'Severity': analysis['severity'],
                    'Finding': issue,
                    'Impact': self._get_issue_impact(issue),
                    'Recommendation': self._get_issue_recommendation(issue),
                    'WellArchitectedRef': 'SEC03-BP02: Grant least privilege access'
                })
            
            # Only add policies with issues or for complete visibility
            if analysis['issues'] or has_wildcard_actions or has_wildcard_resources:
                policy_checks.append({
                    'Resource': f'Policy: {policy_name}',
                    'ResourceType': 'IAMCustomPolicy',
                    'PolicyName': policy_name,
                    'PolicyArn': policy_arn,
                    'Severity': analysis['severity'],
                    'Status': 'Non-Compliant' if analysis['issues'] else 'Review',
                    'StatementCount': statement_count,
                    'PolicySize': policy_size,
                    'PolicyDocument': policy_doc,  # Include for HTML display
                    'HighRiskActions': high_risk_actions,
                    'HasWildcardActions': has_wildcard_actions,
                    'HasWildcardResources': has_wildcard_resources,
                    'HasConditions': has_conditions,
                    'Issues': analysis['issues'] if analysis['issues'] else ['Review of policy recommended - uses wildcard resources'],
                    'DetailedIssues': detailed_issues,
                    'Recommendation': self._get_policy_remediation(analysis['severity'], analysis['issues'])
                })
        
        return policy_checks
    
    def _check_wildcard_actions(self, policy_doc):
        """Check if policy uses wildcard actions"""
        statements = policy_doc.get('Statement', [])
        if not isinstance(statements, list):
            statements = [statements]
        
        for stmt in statements:
            if stmt.get('Effect') == 'Allow':
                actions = stmt.get('Action', [])
                if isinstance(actions, str):
                    actions = [actions]
                if any('*' in action for action in actions):
                    return True
        return False
    
    def _check_wildcard_resources(self, policy_doc):
        """Check if policy uses wildcard resources"""
        statements = policy_doc.get('Statement', [])
        if not isinstance(statements, list):
            statements = [statements]
        
        for stmt in statements:
            if stmt.get('Effect') == 'Allow':
                resources = stmt.get('Resource', [])
                if isinstance(resources, str):
                    resources = [resources]
                if '*' in resources:
                    return True
        return False
    
    def _check_has_conditions(self, policy_doc):
        """Check if policy uses conditions"""
        statements = policy_doc.get('Statement', [])
        if not isinstance(statements, list):
            statements = [statements]
        
        for stmt in statements:
            if stmt.get('Condition'):
                return True
        return False
    
    def _extract_high_risk_actions(self, policy_doc):
        """Extract high-risk actions from policy"""
        high_risk = []
        high_risk_patterns = [
            'iam:*', 's3:*', 'lambda:*', 'ec2:*',
            'iam:AttachUserPolicy', 'iam:AttachRolePolicy',
            'iam:CreateAccessKey', 'iam:PassRole',
            'sts:AssumeRole', 'kms:Decrypt',
            'secretsmanager:GetSecretValue'
        ]
        
        statements = policy_doc.get('Statement', [])
        if not isinstance(statements, list):
            statements = [statements]
        
        for stmt in statements:
            if stmt.get('Effect') == 'Allow':
                actions = stmt.get('Action', [])
                if isinstance(actions, str):
                    actions = [actions]
                for action in actions:
                    if action in high_risk_patterns or action == '*':
                        high_risk.append(action)
        
        return list(set(high_risk))[:5]  # Return up to 5 unique high-risk actions
    
    def _get_issue_impact(self, issue):
        """Get impact description for an issue"""
        if 'admin' in issue.lower():
            return 'Attacker gains full administrative control over AWS account'
        elif 'escalation' in issue.lower():
            return 'Attacker can elevate privileges to gain additional permissions'
        elif 's3:' in issue.lower():
            return 'Sensitive data in S3 buckets can be accessed or exfiltrated'
        elif 'PassRole' in issue:
            return 'Attacker can pass elevated roles to services they control'
        elif 'wildcard' in issue.lower():
            return 'Overly broad permissions increase attack surface'
        else:
            return 'Security posture weakened by excessive permissions'
    
    def _get_issue_recommendation(self, issue):
        """Get recommendation for fixing an issue"""
        if 'admin' in issue.lower() or '*' in issue and 'Action' in issue:
            return 'Replace with specific actions required for the use case'
        elif 'escalation' in issue.lower():
            return 'Add resource-level restrictions and condition keys to limit scope'
        elif 's3:' in issue.lower():
            return 'Restrict to specific bucket ARNs and add MFA conditions for sensitive operations'
        elif 'PassRole' in issue:
            return 'Add PassedToService condition to restrict which services can assume the role'
        elif 'Resource: *' in issue:
            return 'Replace with specific resource ARNs (buckets, functions, tables, etc.)'
        else:
            return 'Review and apply least privilege principle'
    
    def _get_policy_remediation(self, severity, issues):
        """Generate remediation recommendations for policies"""
        recommendations = []
        
        if severity == 'CRITICAL':
            recommendations.append('🚨 CRITICAL: This policy grants excessive privileges that could compromise your AWS account')
            recommendations.append('🔒 Immediate action required: Replace with least-privilege policy')
            recommendations.append('🔒 Use AWS Policy Generator or IAM Access Analyzer to create minimal policies')
        elif severity == 'HIGH':
            recommendations.append('⚠️ HIGH: Policy contains dangerous permission combinations')
            recommendations.append('🔒 Add resource-level restrictions using specific ARNs')
            recommendations.append('🔒 Implement condition keys (e.g., IP restrictions, MFA requirements)')
        elif severity == 'MEDIUM':
            recommendations.append('⚠️ MEDIUM: Policy should be tightened to follow least privilege')
            recommendations.append('🔒 Review each statement and restrict to minimum required permissions')
        elif severity == 'LOW':
            recommendations.append('ℹ️ LOW: Policy follows basic security practices but could be improved')
            recommendations.append('🔒 Consider adding condition keys for additional security')
        
        # Add specific recommendations based on issues
        if any('PassRole' in str(issue) for issue in issues):
            recommendations.append('🔒 PassRole: Add "Condition": {"StringEquals": {"iam:PassedToService": "service.amazonaws.com"}}')
        if any('s3:' in str(issue) for issue in issues):
            recommendations.append('🔒 S3: Restrict to specific bucket ARNs and require MFA for Delete operations')
        if any('admin' in str(issue).lower() for issue in issues):
            recommendations.append('🔒 Admin Access: Break down into separate policies for different functions')
        
        return ' | '.join(recommendations)
    
    def verify_iam(self) -> Dict[str, Any]:
        """Verify IAM configuration with security analysis"""
        results = {
            'title': 'IAM Verification',
            'checks': []
        }
        
        # Analyze Roles
        roles = self.collected_data.get('IAM', {}).get('Roles', [])
        for role_data in roles:
            role = role_data.get('Role', {})
            role_name = role.get('RoleName', '')
            attached_policies = role_data.get('AttachedPolicies', [])
            inline_policies = role_data.get('InlinePolicies', {})
            
            all_issues = []
            max_severity = 'INFO'
            
            # Check for AWS managed admin policies
            for policy in attached_policies:
                policy_arn = policy.get('PolicyArn', '')
                policy_name = policy.get('PolicyName', '')
                
                if 'AdministratorAccess' in policy_arn:
                    all_issues.append('🚨 CRITICAL: AdministratorAccess policy attached')
                    max_severity = 'CRITICAL'
                elif 'PowerUserAccess' in policy_arn:
                    all_issues.append('⚠️ HIGH: PowerUserAccess policy attached')
                    if max_severity not in ['CRITICAL']:
                        max_severity = 'HIGH'
            
            # Analyze inline policies
            for policy_name, policy_doc in inline_policies.items():
                analysis = self._analyze_iam_policy_security(policy_doc, policy_name, role_name)
                if analysis['issues']:
                    all_issues.extend([f"{issue} (inline: {policy_name})" for issue in analysis['issues']])
                    
                    # Update severity
                    if analysis['severity'] == 'CRITICAL' or max_severity == 'CRITICAL':
                        max_severity = 'CRITICAL'
                    elif analysis['severity'] == 'HIGH' and max_severity not in ['CRITICAL']:
                        max_severity = 'HIGH'
                    elif analysis['severity'] == 'MEDIUM' and max_severity not in ['CRITICAL', 'HIGH']:
                        max_severity = 'MEDIUM'
                    elif analysis['severity'] == 'LOW' and max_severity == 'INFO':
                        max_severity = 'LOW'
            
            # Check assume role policy (trust policy)
            assume_role_policy = role.get('AssumeRolePolicyDocument', {})
            if assume_role_policy:
                statements = assume_role_policy.get('Statement', [])
                if not isinstance(statements, list):
                    statements = [statements]
                
                for statement in statements:
                    if statement.get('Effect') == 'Allow':
                        principal = statement.get('Principal', {})
                        
                        # Check for overly permissive trust policies
                        if isinstance(principal, dict):
                            aws_principals = principal.get('AWS', [])
                            if isinstance(aws_principals, str):
                                aws_principals = [aws_principals]
                            
                            # Check for wildcards in trust policy
                            if '*' in aws_principals:
                                all_issues.append('🚨 CRITICAL: Trust policy allows ANY AWS account (*)')
                                max_severity = 'CRITICAL'
                            
                            # Check for root account access
                            root_access = [p for p in aws_principals if ':root' in str(p)]
                            if root_access:
                                all_issues.append('⚠️ MEDIUM: Trust policy allows root account access')
                                if max_severity not in ['CRITICAL', 'HIGH', 'MEDIUM']:
                                    max_severity = 'MEDIUM'
            
            # Only add to results if there are issues or for summary
            if all_issues or max_severity != 'INFO':
                results['checks'].append({
                    'Resource': f'Role: {role_name}',
                    'ResourceType': 'IAMRole',
                    'Severity': max_severity,
                    'Status': 'Non-Compliant' if all_issues else 'Review',
                    'AttachedPolicies': len(attached_policies),
                    'InlinePolicies': len(inline_policies),
                    'Issues': all_issues if all_issues else ['Review of role recommended - has attached permissions'],
                    'Recommendation': self._get_iam_remediation(max_severity, all_issues)
                })
        
        # Check Users (IAM users should generally not exist in favor of SSO/Federation)
        users = self.collected_data.get('IAM', {}).get('Users', [])
        if len(users) > 0:
            results['checks'].append({
                'Resource': f'IAM Users',
                'ResourceType': 'IAMUsers',
                'Severity': 'MEDIUM',
                'Status': 'Review Required',
                'UserCount': len(users),
                'Issues': [f'⚠️ MEDIUM: {len(users)} IAM user(s) found - consider using AWS SSO/Identity Center instead'],
                'Recommendation': 'Migrate to AWS IAM Identity Center (SSO) for human users. Use IAM roles for service accounts.'
            })
        
        # Analyze Customer-Managed Policies
        custom_policies = self.collected_data.get('IAM', {}).get('CustomerManagedPolicies', [])
        if custom_policies:
            policy_analysis_results = self._analyze_custom_policies(custom_policies)
            results['checks'].extend(policy_analysis_results)
        
        # If no issues found, add summary
        if not results['checks']:
            results['checks'].append({
                'Resource': 'IAM Configuration',
                'ResourceType': 'Summary',
                'Severity': 'INFO',
                'Status': 'No Critical Issues',
                'Details': f'{len(roles)} role(s) reviewed, no critical security violations detected'
            })
        
        return results
    
    def _get_iam_remediation(self, severity, issues):
        """Generate IAM remediation recommendations"""
        recommendations = []
        
        if severity == 'CRITICAL':
            recommendations.append('🔒 CRITICAL: Remove overly permissive policies immediately')
            recommendations.append('🔒 Apply least privilege principle - grant minimum required permissions')
            recommendations.append('🔒 Use managed policies with specific resource ARNs')
        elif severity == 'HIGH':
            recommendations.append('🔒 HIGH: Reduce permission scope to specific resources')
            recommendations.append('🔒 Add condition keys to restrict usage')
            recommendations.append('🔒 Remove privilege escalation paths')
        elif severity == 'MEDIUM':
            recommendations.append('🔒 MEDIUM: Review and tighten permissions')
            recommendations.append('🔒 Add resource-level restrictions')
        elif severity == 'LOW':
            recommendations.append('🔒 Review permissions for least privilege compliance')
        
        # Check for specific issues
        if any('PassRole' in str(issue) for issue in issues):
            recommendations.append('🔒 Add conditions to iam:PassRole (e.g., iam:PassedToService)')
        
        if any('AdministratorAccess' in str(issue) for issue in issues):
            recommendations.append('🔒 Replace AdministratorAccess with job-specific managed policies')
        
        return ' | '.join(recommendations) if recommendations else 'Review for least privilege'
    
    def verify_monitoring(self) -> Dict[str, Any]:
        """Verify CloudWatch monitoring configuration"""
        results = {
            'title': 'Monitoring Verification',
            'alarms': [],
            'log_groups': []
        }
        
        # CloudWatch Alarms
        alarms = self.collected_data.get('CloudWatch', {}).get('Alarms', [])
        for alarm in alarms:
            results['alarms'].append({
                'AlarmName': alarm.get('AlarmName'),
                'MetricName': alarm.get('MetricName'),
                'Namespace': alarm.get('Namespace'),
                'State': alarm.get('StateValue'),
                'ActionsEnabled': alarm.get('ActionsEnabled'),
                'AlarmActions': len(alarm.get('AlarmActions', []))
            })
        
        # Log Groups
        log_groups = self.collected_data.get('CloudWatch', {}).get('LogGroups', [])
        for log_group in log_groups:
            results['log_groups'].append({
                'LogGroupName': log_group.get('logGroupName'),
                'RetentionDays': log_group.get('retentionInDays', 'Never Expire'),
                'StoredBytes': log_group.get('storedBytes', 0)
            })
        
        return results
    
    def verify_bedrock(self) -> Dict[str, Any]:
        """Verify Amazon Bedrock security configurations"""
        results = {
            'title': 'Amazon Bedrock Security Verification',
            'checks': []
        }
        
        bedrock_data = self.collected_data.get('Bedrock', {})
        
        # Check if data collection had errors
        if 'Error' in bedrock_data:
            results['checks'].append({
                'Resource': 'Bedrock Collection',
                'Status': 'Error',
                'Severity': 'INFO',
                'Issue': f"Data collection error: {bedrock_data.get('Error')}",
                'Details': 'Enable Bedrock permissions to perform security checks'
            })
            return results
        
        # Check Guardrails configuration
        guardrails = bedrock_data.get('Guardrails', [])
        custom_models = bedrock_data.get('CustomModels', [])
        
        if custom_models and not guardrails:
            results['checks'].append({
                'Resource': 'Bedrock Guardrails',
                'Status': 'Missing',
                'Severity': 'HIGH',
                'Issue': f'Custom models deployed without guardrails',
                'Details': f'{len(custom_models)} custom model(s) found but no guardrails configured',
                'Recommendation': 'Configure Bedrock Guardrails for PII detection, content filtering, and topic denial'
            })
        
        # Check each guardrail configuration
        for guardrail in guardrails:
            guardrail_name = guardrail.get('name', 'Unknown')
            guardrail_id = guardrail.get('guardrailId', 'Unknown')
            
            issues = []
            
            # Check content policy
            content_policy = guardrail.get('contentPolicy', {})
            if not content_policy:
                issues.append('No content filtering policy configured')
            
            # Check sensitive information policy (PII)
            sensitive_info_policy = guardrail.get('sensitiveInformationPolicy', {})
            if not sensitive_info_policy:
                issues.append('No PII detection/redaction configured')
            
            # Check topic policy
            topic_policy = guardrail.get('topicPolicy', {})
            if not topic_policy:
                issues.append('No topic denial policy configured')
            
            # Check word policy
            word_policy = guardrail.get('wordPolicy', {})
            if not word_policy:
                issues.append('No word filtering configured')
            
            if issues:
                results['checks'].append({
                    'Resource': f'Guardrail: {guardrail_name}',
                    'GuardrailId': guardrail_id,
                    'Status': 'Incomplete',
                    'Severity': 'MEDIUM',
                    'Issue': 'Incomplete guardrail configuration',
                    'Details': '; '.join(issues),
                    'Recommendation': 'Enable all guardrail policies for comprehensive protection'
                })
            else:
                results['checks'].append({
                    'Resource': f'Guardrail: {guardrail_name}',
                    'GuardrailId': guardrail_id,
                    'Status': 'Compliant',
                    'Severity': 'INFO',
                    'Details': 'All guardrail policies configured'
                })
        
        # Check CloudWatch logging
        logging_config = bedrock_data.get('LoggingConfiguration', {})
        logging_enabled = logging_config.get('LoggingEnabled', False)
        
        if not logging_enabled:
            results['checks'].append({
                'Resource': 'Bedrock CloudWatch Logging',
                'Status': 'Disabled',
                'Severity': 'MEDIUM',
                'Issue': 'CloudWatch logging not enabled for Bedrock',
                'Details': 'Model invocations are not being logged',
                'Recommendation': 'Enable CloudWatch logging for audit trail and monitoring'
            })
        
        # Check model customization jobs for encryption
        customization_jobs = bedrock_data.get('ModelCustomizationJobs', [])
        for job in customization_jobs:
            job_name = job.get('jobName', 'Unknown')
            output_config = job.get('outputDataConfig', {})
            
            # Check if KMS encryption is used
            kms_key_id = output_config.get('kmsKeyId')
            if not kms_key_id:
                results['checks'].append({
                    'Resource': f'Customization Job: {job_name}',
                    'Status': 'Unencrypted',
                    'Severity': 'MEDIUM',
                    'Issue': 'Model artifacts not encrypted with customer-managed KMS key',
                    'Details': 'Using default encryption instead of CMK',
                    'Recommendation': 'Use customer-managed KMS keys for model artifact encryption'
                })
        
        # If no checks were added, indicate no resources found
        if not results['checks']:
            results['checks'].append({
                'Resource': 'Amazon Bedrock',
                'Status': 'No Resources',
                'Severity': 'INFO',
                'Details': 'No Bedrock resources found in this region'
            })
        
        return results
    
    def verify_sagemaker(self) -> Dict[str, Any]:
        """Verify Amazon SageMaker security configurations"""
        results = {
            'title': 'Amazon SageMaker Security Verification',
            'checks': []
        }
        
        sagemaker_data = self.collected_data.get('SageMaker', {})
        
        # Check if data collection had errors
        if 'Error' in sagemaker_data:
            results['checks'].append({
                'Resource': 'SageMaker Collection',
                'Status': 'Error',
                'Severity': 'INFO',
                'Issue': f"Data collection error: {sagemaker_data.get('Error')}",
                'Details': 'Enable SageMaker permissions to perform security checks'
            })
            return results
        
        # Check Notebook Instances
        notebooks = sagemaker_data.get('NotebookInstances', [])
        for notebook in notebooks:
            notebook_name = notebook.get('NotebookInstanceName', 'Unknown')
            issues = []
            severity = 'INFO'
            
            # CRITICAL: Direct internet access
            direct_internet = notebook.get('DirectInternetAccess', 'Enabled')
            if direct_internet == 'Enabled':
                issues.append('🚨 CRITICAL: Direct internet access enabled')
                severity = 'CRITICAL'
            
            # HIGH: Root access enabled
            root_access = notebook.get('RootAccess', 'Enabled')
            if root_access == 'Enabled':
                issues.append('⚠️ HIGH: Root access enabled')
                if severity == 'INFO':
                    severity = 'HIGH'
            
            # MEDIUM: Not in VPC
            subnet_id = notebook.get('SubnetId')
            if not subnet_id:
                issues.append('⚠️ MEDIUM: Not deployed in VPC')
                if severity == 'INFO':
                    severity = 'MEDIUM'
            
            # MEDIUM: No encryption
            kms_key_id = notebook.get('KmsKeyId')
            if not kms_key_id:
                issues.append('⚠️ MEDIUM: No customer-managed encryption key')
                if severity == 'INFO':
                    severity = 'MEDIUM'
            
            if issues:
                results['checks'].append({
                    'Resource': f'Notebook: {notebook_name}',
                    'ResourceType': 'NotebookInstance',
                    'Status': 'Non-Compliant',
                    'Severity': severity,
                    'Issues': issues,
                    'DirectInternetAccess': direct_internet,
                    'RootAccess': root_access,
                    'VPC': 'Yes' if subnet_id else 'No',
                    'Encrypted': 'CMK' if kms_key_id else 'Default',
                    'Recommendation': self._get_notebook_remediation(direct_internet, root_access, subnet_id, kms_key_id)
                })
            else:
                results['checks'].append({
                    'Resource': f'Notebook: {notebook_name}',
                    'ResourceType': 'NotebookInstance',
                    'Status': 'Compliant',
                    'Severity': 'INFO',
                    'Details': 'Notebook follows security best practices'
                })
        
        # Check SageMaker Domains (Studio)
        domains = sagemaker_data.get('Domains', [])
        for domain in domains:
            domain_id = domain.get('DomainId', 'Unknown')
            domain_name = domain.get('DomainName', 'Unknown')
            issues = []
            severity = 'INFO'
            
            # Check authentication mode
            auth_mode = domain.get('AuthMode', 'IAM')
            if auth_mode == 'IAM':
                issues.append('ℹ️ INFO: Using IAM authentication (consider SSO for better management)')
            
            # Check VPC-only mode
            app_network_access = domain.get('AppNetworkAccessType', 'PublicInternetOnly')
            if app_network_access == 'PublicInternetOnly':
                issues.append('⚠️ HIGH: Public internet access enabled')
                severity = 'HIGH'
            
            # Check default user settings
            default_settings = domain.get('DefaultUserSettings', {})
            execution_role = default_settings.get('ExecutionRole')
            
            if issues or severity != 'INFO':
                results['checks'].append({
                    'Resource': f'Domain: {domain_name}',
                    'DomainId': domain_id,
                    'ResourceType': 'SageMakerDomain',
                    'Status': 'Review Required',
                    'Severity': severity,
                    'Issues': issues,
                    'AuthMode': auth_mode,
                    'NetworkAccess': app_network_access,
                    'Recommendation': 'Use VPC-only mode and SSO authentication for production domains'
                })
        
        # Check Training Jobs
        training_jobs = sagemaker_data.get('TrainingJobs', [])
        for job in training_jobs[:20]:  # Check last 20 jobs
            job_name = job.get('TrainingJobName', 'Unknown')
            issues = []
            severity = 'INFO'
            
            # Check network isolation
            enable_network_isolation = job.get('EnableNetworkIsolation', False)
            if not enable_network_isolation:
                issues.append('⚠️ MEDIUM: Network isolation not enabled')
                severity = 'MEDIUM'
            
            # Check VPC configuration
            vpc_config = job.get('VpcConfig')
            if not vpc_config:
                issues.append('⚠️ MEDIUM: Not running in VPC')
                if severity == 'INFO':
                    severity = 'MEDIUM'
            
            # Check encryption
            resource_config = job.get('ResourceConfig', {})
            volume_kms_key = resource_config.get('VolumeKmsKeyId')
            if not volume_kms_key:
                issues.append('⚠️ LOW: No customer-managed encryption key for volumes')
                if severity == 'INFO':
                    severity = 'LOW'
            
            if issues:
                results['checks'].append({
                    'Resource': f'Training Job: {job_name}',
                    'ResourceType': 'TrainingJob',
                    'Status': 'Review Required',
                    'Severity': severity,
                    'Issues': issues,
                    'NetworkIsolation': enable_network_isolation,
                    'VPC': 'Yes' if vpc_config else 'No',
                    'Recommendation': 'Enable network isolation and run in VPC for production training jobs'
                })
        
        # Check Endpoints
        endpoints = sagemaker_data.get('Endpoints', [])
        for endpoint in endpoints:
            endpoint_name = endpoint.get('EndpointName', 'Unknown')
            issues = []
            severity = 'INFO'
            
            # Check data capture (could expose data to S3)
            data_capture_config = endpoint.get('DataCaptureConfig', {})
            if data_capture_config.get('EnableCapture'):
                destination = data_capture_config.get('DestinationS3Uri', '')
                issues.append(f'ℹ️ INFO: Data capture enabled to {destination} - verify S3 bucket security')
            
            # Get endpoint config to check for encryption and VPC
            endpoint_config_name = endpoint.get('EndpointConfigName')
            endpoint_configs = sagemaker_data.get('EndpointConfigs', [])
            endpoint_config = next((ec for ec in endpoint_configs if ec.get('EndpointConfigName') == endpoint_config_name), None)
            
            if endpoint_config:
                kms_key_id = endpoint_config.get('KmsKeyId')
                if not kms_key_id:
                    issues.append('⚠️ MEDIUM: No customer-managed encryption key')
                    severity = 'MEDIUM'
            
            # Always include endpoints in the report for visibility, even if no issues
            # Include full endpoint and config data for HTML drill-down
            check_entry = {
                'Resource': f'Endpoint: {endpoint_name}',
                'ResourceType': 'Endpoint',
                'Status': 'Review Required' if (issues and severity != 'INFO') else 'Compliant',
                'Severity': severity,
                'Issues': issues if issues else ['✓ No security issues detected'],
                'Recommendation': 'Use customer-managed KMS keys and verify data capture S3 bucket security' if (issues and severity != 'INFO') else 'Endpoint properly configured',
                '_endpoint_data': endpoint,  # Full endpoint data for drill-down
                '_endpoint_config': endpoint_config if endpoint_config else {}  # Full config data for drill-down
            }
            
            results['checks'].append(check_entry)
        
        # Check Feature Groups (Feature Store)
        feature_groups = sagemaker_data.get('FeatureGroups', [])
        for fg in feature_groups:
            fg_name = fg.get('FeatureGroupName', 'Unknown')
            issues = []
            severity = 'INFO'
            
            # Check online store encryption
            online_store_config = fg.get('OnlineStoreConfig', {})
            if online_store_config:
                security_config = online_store_config.get('SecurityConfig', {})
                kms_key_id = security_config.get('KmsKeyId')
                if not kms_key_id:
                    issues.append('⚠️ MEDIUM: Online store not encrypted with customer-managed key')
                    severity = 'MEDIUM'
            
            # Check offline store encryption
            offline_store_config = fg.get('OfflineStoreConfig', {})
            if offline_store_config:
                s3_storage = offline_store_config.get('S3StorageConfig', {})
                kms_key_id = s3_storage.get('KmsKeyId')
                if not kms_key_id:
                    issues.append('⚠️ MEDIUM: Offline store not encrypted with customer-managed key')
                    if severity == 'INFO':
                        severity = 'MEDIUM'
            
            if issues:
                results['checks'].append({
                    'Resource': f'Feature Group: {fg_name}',
                    'ResourceType': 'FeatureGroup',
                    'Status': 'Review Required',
                    'Severity': severity,
                    'Issues': issues,
                    'Recommendation': 'Use customer-managed KMS keys for both online and offline feature stores'
                })
        
        # If no checks were added, indicate no resources found
        if not results['checks']:
            results['checks'].append({
                'Resource': 'Amazon SageMaker',
                'Status': 'No Resources',
                'Severity': 'INFO',
                'Details': 'No SageMaker resources found in this region'
            })
        
        return results
    
    def _get_notebook_remediation(self, direct_internet, root_access, subnet_id, kms_key_id):
        """Generate remediation recommendations for notebook instances"""
        recommendations = []
        
        if direct_internet == 'Enabled':
            recommendations.append('🔒 CRITICAL: Disable direct internet access - use VPC with NAT gateway')
        if root_access == 'Enabled':
            recommendations.append('🔒 HIGH: Disable root access to prevent privilege escalation')
        if not subnet_id:
            recommendations.append('🔒 MEDIUM: Deploy notebook in private VPC subnet')
        if not kms_key_id:
            recommendations.append('🔒 MEDIUM: Enable encryption with customer-managed KMS key')
        
        return ' | '.join(recommendations) if recommendations else 'Compliant'
    
    def verify_cis_benchmarks(self) -> Dict[str, Any]:
        """Verify CIS AWS Foundations Benchmark v1.4.0 - All 54 Controls"""
        results = {
            'title': 'CIS AWS Foundations Benchmark v1.4.0',
            'checks': []
        }
        
        security_audit = self.collected_data.get('SecurityAudit', {})
        iam_data = self.collected_data.get('IAM', {})
        s3_data = self.collected_data.get('S3', {})
        vpc_data = self.collected_data.get('VPC', {})
        
        # ====================
        # SECTION 1: Identity and Access Management
        # ====================
        
        # CIS 1.1: Maintain current contact details
        results['checks'].append({
            'BenchmarkID': 'CIS-1.1',
            'Resource': 'Account Contact Details',
            'Status': 'NOT_VERIFIED',
            'Severity': 'INFO',
            'Finding': 'Manual verification required',
            'Recommendation': 'Verify AWS account contact details are current in AWS Console > My Account'
        })
        
        # CIS 1.2: Ensure security contact information is registered
        results['checks'].append({
            'BenchmarkID': 'CIS-1.2',
            'Resource': 'Security Contact Information',
            'Status': 'NOT_VERIFIED',
            'Severity': 'INFO',
            'Finding': 'Manual verification required',
            'Recommendation': 'Verify security contact email is registered in AWS Console > My Account > Alternate Contacts'
        })
        
        # CIS 1.3: Ensure security questions are registered
        results['checks'].append({
            'BenchmarkID': 'CIS-1.3',
            'Resource': 'Security Questions',
            'Status': 'NOT_VERIFIED',
            'Severity': 'INFO',
            'Finding': 'Manual verification required',
            'Recommendation': 'Verify security questions are registered in AWS Console > My Account'
        })
        
        # CIS 1.4: Ensure no root account access key exists
        root_checks = security_audit.get('RootAccountChecks', {})
        if root_checks:
            has_access_keys = root_checks.get('AccessKey1Active') or root_checks.get('AccessKey2Active')
            if has_access_keys:
                results['checks'].append({
                    'BenchmarkID': 'CIS-1.4',
                    'Resource': 'Root Account Access Keys',
                    'Status': 'FAIL',
                    'Severity': 'CRITICAL',
                    'Finding': 'Root account has active access keys',
                    'Recommendation': '🔒 CRITICAL: Delete root access keys immediately'
                })
            else:
                results['checks'].append({
                    'BenchmarkID': 'CIS-1.4',
                    'Resource': 'Root Account Access Keys',
                    'Status': 'PASS',
                    'Severity': 'INFO',
                    'Finding': 'No root account access keys found',
                    'Recommendation': 'Compliant'
                })
        else:
            results['checks'].append({
                'BenchmarkID': 'CIS-1.4',
                'Resource': 'Root Account Access Keys',
                'Status': 'NOT_VERIFIED',
                'Severity': 'INFO',
                'Finding': 'Root account check data not available',
                'Recommendation': 'Enable IAM credential report generation'
            })
        
        # CIS 1.5-1.11: Password Policy (combined checks)
        pw_policy = security_audit.get('IAMPasswordPolicy', {})
        if pw_policy.get('Exists'):
            policy_details = pw_policy.get('Policy', {})
            
            # CIS 1.5: Ensure IAM password policy requires minimum length of 14 or greater
            min_length = policy_details.get('MinimumPasswordLength', 0)
            results['checks'].append({
                'BenchmarkID': 'CIS-1.5',
                'Resource': 'IAM Password Policy - Min Length',
                'Status': 'PASS' if min_length >= 14 else 'FAIL',
                'Severity': 'MEDIUM' if min_length < 14 else 'INFO',
                'Finding': f'Minimum password length: {min_length}' if min_length < 14 else 'Password length requirement met (≥14)',
                'Recommendation': 'Set minimum password length to 14 or greater' if min_length < 14 else 'Compliant'
            })
            
            # CIS 1.6: Ensure IAM password policy prevents password reuse
            reuse = policy_details.get('PasswordReusePrevention', 0)
            results['checks'].append({
                'BenchmarkID': 'CIS-1.6',
                'Resource': 'IAM Password Policy - Reuse Prevention',
                'Status': 'PASS' if reuse >= 24 else 'FAIL',
                'Severity': 'MEDIUM' if reuse < 24 else 'INFO',
                'Finding': f'Password reuse prevention: {reuse} passwords' if reuse < 24 else 'Password reuse prevention enabled (≥24)',
                'Recommendation': 'Set password reuse prevention to 24 or more' if reuse < 24 else 'Compliant'
            })
            
            # CIS 1.7: Ensure IAM password policy requires at least one uppercase letter
            results['checks'].append({
                'BenchmarkID': 'CIS-1.7',
                'Resource': 'IAM Password Policy - Uppercase',
                'Status': 'PASS' if policy_details.get('RequireUppercaseCharacters') else 'FAIL',
                'Severity': 'MEDIUM' if not policy_details.get('RequireUppercaseCharacters') else 'INFO',
                'Finding': 'Uppercase character requirement enabled' if policy_details.get('RequireUppercaseCharacters') else 'Uppercase characters not required',
                'Recommendation': 'Enable uppercase character requirement' if not policy_details.get('RequireUppercaseCharacters') else 'Compliant'
            })
            
            # CIS 1.8: Ensure IAM password policy requires at least one lowercase letter
            results['checks'].append({
                'BenchmarkID': 'CIS-1.8',
                'Resource': 'IAM Password Policy - Lowercase',
                'Status': 'PASS' if policy_details.get('RequireLowercaseCharacters') else 'FAIL',
                'Severity': 'MEDIUM' if not policy_details.get('RequireLowercaseCharacters') else 'INFO',
                'Finding': 'Lowercase character requirement enabled' if policy_details.get('RequireLowercaseCharacters') else 'Lowercase characters not required',
                'Recommendation': 'Enable lowercase character requirement' if not policy_details.get('RequireLowercaseCharacters') else 'Compliant'
            })
            
            # CIS 1.9: Ensure IAM password policy requires at least one symbol
            results['checks'].append({
                'BenchmarkID': 'CIS-1.9',
                'Resource': 'IAM Password Policy - Symbols',
                'Status': 'PASS' if policy_details.get('RequireSymbols') else 'FAIL',
                'Severity': 'MEDIUM' if not policy_details.get('RequireSymbols') else 'INFO',
                'Finding': 'Symbol requirement enabled' if policy_details.get('RequireSymbols') else 'Symbols not required',
                'Recommendation': 'Enable symbol requirement' if not policy_details.get('RequireSymbols') else 'Compliant'
            })
            
            # CIS 1.10: Ensure IAM password policy requires at least one number
            results['checks'].append({
                'BenchmarkID': 'CIS-1.10',
                'Resource': 'IAM Password Policy - Numbers',
                'Status': 'PASS' if policy_details.get('RequireNumbers') else 'FAIL',
                'Severity': 'MEDIUM' if not policy_details.get('RequireNumbers') else 'INFO',
                'Finding': 'Number requirement enabled' if policy_details.get('RequireNumbers') else 'Numbers not required',
                'Recommendation': 'Enable number requirement' if not policy_details.get('RequireNumbers') else 'Compliant'
            })
            
            # CIS 1.11: Ensure IAM password policy expires passwords within 90 days or less
            max_age = policy_details.get('MaxPasswordAge', 0)
            results['checks'].append({
                'BenchmarkID': 'CIS-1.11',
                'Resource': 'IAM Password Policy - Expiration',
                'Status': 'PASS' if 0 < max_age <= 90 else 'FAIL',
                'Severity': 'MEDIUM' if not (0 < max_age <= 90) else 'INFO',
                'Finding': f'Password expiration: {max_age} days' if max_age > 0 else 'Password expiration not enabled',
                'Recommendation': 'Set password expiration to 90 days or less' if not (0 < max_age <= 90) else 'Compliant'
            })
        else:
            # No password policy - mark all as FAIL
            for cis_id in ['1.5', '1.6', '1.7', '1.8', '1.9', '1.10', '1.11']:
                results['checks'].append({
                    'BenchmarkID': f'CIS-{cis_id}',
                    'Resource': 'IAM Password Policy',
                    'Status': 'FAIL',
                    'Severity': 'HIGH',
                    'Finding': 'No password policy configured',
                    'Recommendation': '🔒 HIGH: Configure CIS-compliant password policy'
                })
        
        # CIS 1.12: Ensure no root account access key exists (duplicate of 1.4)
        results['checks'].append({
            'BenchmarkID': 'CIS-1.12',
            'Resource': 'Root Account Access Keys',
            'Status': 'PASS' if root_checks and not (root_checks.get('AccessKey1Active') or root_checks.get('AccessKey2Active')) else 'FAIL' if root_checks else 'NOT_VERIFIED',
            'Severity': 'CRITICAL' if root_checks and (root_checks.get('AccessKey1Active') or root_checks.get('AccessKey2Active')) else 'INFO',
            'Finding': 'Root access keys check - see CIS-1.4',
            'Recommendation': 'See CIS-1.4'
        })
        
        # CIS 1.13: Ensure MFA is enabled for the root account
        results['checks'].append({
            'BenchmarkID': 'CIS-1.13',
            'Resource': 'Root Account MFA',
            'Status': 'PASS' if root_checks and root_checks.get('MFAActive') else 'FAIL' if root_checks else 'NOT_VERIFIED',
            'Severity': 'CRITICAL' if root_checks and not root_checks.get('MFAActive') else 'INFO',
            'Finding': 'Root MFA enabled' if root_checks and root_checks.get('MFAActive') else 'Root MFA not enabled',
            'Recommendation': '🔒 CRITICAL: Enable MFA for root account' if root_checks and not root_checks.get('MFAActive') else 'Compliant'
        })
        
        # CIS 1.14: Ensure hardware MFA is enabled for the root account
        results['checks'].append({
            'BenchmarkID': 'CIS-1.14',
            'Resource': 'Root Account Hardware MFA',
            'Status': 'NOT_VERIFIED',
            'Severity': 'INFO',
            'Finding': 'Hardware MFA requires manual verification',
            'Recommendation': 'Verify hardware MFA is enabled for root account'
        })
        
        # CIS 1.15: Ensure security questions are registered in the AWS account
        results['checks'].append({
            'BenchmarkID': 'CIS-1.15',
            'Resource': 'Security Questions',
            'Status': 'NOT_VERIFIED',
            'Severity': 'INFO',
            'Finding': 'Manual verification required - duplicate of CIS-1.3',
            'Recommendation': 'See CIS-1.3'
        })
        
        # CIS 1.16: Ensure IAM policies are attached only to groups or roles
        users = iam_data.get('Users', [])
        users_with_policies = [u for u in users if u.get('AttachedPolicies') or u.get('InlinePolicies')]
        if users:
            results['checks'].append({
                'BenchmarkID': 'CIS-1.16',
                'Resource': 'IAM Policy Attachment',
                'Status': 'FAIL' if users_with_policies else 'PASS',
                'Severity': 'MEDIUM' if users_with_policies else 'INFO',
                'Finding': f'{len(users_with_policies)} user(s) have policies attached directly' if users_with_policies else 'Policies attached only to groups/roles',
                'Recommendation': 'Attach policies to groups/roles, not users' if users_with_policies else 'Compliant'
            })
        else:
            results['checks'].append({
                'BenchmarkID': 'CIS-1.16',
                'Resource': 'IAM Policy Attachment',
                'Status': 'NOT_VERIFIED',
                'Severity': 'INFO',
                'Finding': 'No IAM users data available',
                'Recommendation': 'Collect IAM user data'
            })
        
        # CIS 1.17: Maintain current contact details - duplicate of 1.1
        results['checks'].append({
            'BenchmarkID': 'CIS-1.17',
            'Resource': 'Contact Details',
            'Status': 'NOT_VERIFIED',
            'Severity': 'INFO',
            'Finding': 'Duplicate of CIS-1.1',
            'Recommendation': 'See CIS-1.1'
        })
        
        # CIS 1.18: Ensure security contact information is registered - duplicate of 1.2
        results['checks'].append({
            'BenchmarkID': 'CIS-1.18',
            'Resource': 'Security Contact',
            'Status': 'NOT_VERIFIED',
            'Severity': 'INFO',
            'Finding': 'Duplicate of CIS-1.2',
            'Recommendation': 'See CIS-1.2'
        })
        
        # CIS 1.19: Ensure IAM instance roles are used for AWS resource access from instances
        results['checks'].append({
            'BenchmarkID': 'CIS-1.19',
            'Resource': 'EC2 Instance Roles',
            'Status': 'NOT_VERIFIED',
            'Severity': 'INFO',
            'Finding': 'Manual verification required',
            'Recommendation': 'Verify EC2 instances use IAM roles instead of embedded credentials'
        })
        
        # CIS 1.20: Ensure a support role has been created
        results['checks'].append({
            'BenchmarkID': 'CIS-1.20',
            'Resource': 'Support Role',
            'Status': 'NOT_VERIFIED',
            'Severity': 'INFO',
            'Finding': 'Manual verification required',
            'Recommendation': 'Verify IAM role with AWSSupportAccess policy exists'
        })
        
        # CIS 1.21: Do not setup access keys during initial user setup for all IAM users that have a console password
        results['checks'].append({
            'BenchmarkID': 'CIS-1.21',
            'Resource': 'IAM User Setup',
            'Status': 'NOT_VERIFIED',
            'Severity': 'INFO',
            'Finding': 'Manual verification required',
            'Recommendation': 'Review user creation process to ensure access keys not created with console password'
        })
        
        # CIS 1.22: Ensure IAM policies that allow full "*:*" administrative privileges are not created
        policies = iam_data.get('CustomerManagedPolicies', [])
        admin_policies = []
        for policy in policies:
            policy_doc = policy.get('PolicyDocument', {})
            for statement in policy_doc.get('Statement', []):
                if (statement.get('Effect') == 'Allow' and 
                    '*' in str(statement.get('Action', [])) and 
                    '*' in str(statement.get('Resource', []))):
                    admin_policies.append(policy.get('PolicyName'))
                    break
        
        if policies:
            results['checks'].append({
                'BenchmarkID': 'CIS-1.22',
                'Resource': 'IAM Administrative Policies',
                'Status': 'FAIL' if admin_policies else 'PASS',
                'Severity': 'HIGH' if admin_policies else 'INFO',
                'Finding': f'{len(admin_policies)} policy/policies with full "*:*" privileges' if admin_policies else 'No overly permissive policies found',
                'Recommendation': f'Review and restrict: {", ".join(admin_policies[:3])}' if admin_policies else 'Compliant'
            })
        else:
            results['checks'].append({
                'BenchmarkID': 'CIS-1.22',
                'Resource': 'IAM Administrative Policies',
                'Status': 'NOT_VERIFIED',
                'Severity': 'INFO',
                'Finding': 'No customer managed policies data available',
                'Recommendation': 'Collect IAM policy data'
            })
        
        # ====================
        # SECTION 2: Storage
        # ====================
        
        # CIS 2.1.1: Ensure S3 buckets employ server-side encryption
        buckets = s3_data.get('Buckets', [])
        if buckets:
            unencrypted = [b for b in buckets if not b.get('Encryption', {}).get('Enabled')]
            results['checks'].append({
                'BenchmarkID': 'CIS-2.1.1',
                'Resource': 'S3 Bucket Encryption',
                'Status': 'FAIL' if unencrypted else 'PASS',
                'Severity': 'HIGH' if unencrypted else 'INFO',
                'Finding': f'{len(unencrypted)} bucket(s) without server-side encryption' if unencrypted else 'All buckets encrypted',
                'Recommendation': f'Enable encryption on: {", ".join([b.get("Name") for b in unencrypted[:3]])}' if unencrypted else 'Compliant'
            })
        else:
            results['checks'].append({
                'BenchmarkID': 'CIS-2.1.1',
                'Resource': 'S3 Bucket Encryption',
                'Status': 'NOT_VERIFIED',
                'Severity': 'INFO',
                'Finding': 'No S3 bucket data available',
                'Recommendation': 'Collect S3 bucket data'
            })
        
        # CIS 2.1.2: Ensure S3 bucket access logging is enabled
        if buckets:
            no_logging = [b for b in buckets if not b.get('Logging', {}).get('Enabled')]
            results['checks'].append({
                'BenchmarkID': 'CIS-2.1.2',
                'Resource': 'S3 Bucket Logging',
                'Status': 'FAIL' if no_logging else 'PASS',
                'Severity': 'MEDIUM' if no_logging else 'INFO',
                'Finding': f'{len(no_logging)} bucket(s) without access logging' if no_logging else 'All buckets have logging',
                'Recommendation': f'Enable logging on: {", ".join([b.get("Name") for b in no_logging[:3]])}' if no_logging else 'Compliant'
            })
        else:
            results['checks'].append({
                'BenchmarkID': 'CIS-2.1.2',
                'Resource': 'S3 Bucket Logging',
                'Status': 'NOT_VERIFIED',
                'Severity': 'INFO',
                'Finding': 'No S3 bucket data available',
                'Recommendation': 'Collect S3 bucket data'
            })
        
        # CIS 2.1.3: Ensure S3 buckets have "Block all public access" enabled
        if buckets:
            public_buckets = [b for b in buckets if not b.get('PublicAccessBlock', {}).get('BlockPublicAcls', True)]
            results['checks'].append({
                'BenchmarkID': 'CIS-2.1.3',
                'Resource': 'S3 Public Access Block',
                'Status': 'FAIL' if public_buckets else 'PASS',
                'Severity': 'CRITICAL' if public_buckets else 'INFO',
                'Finding': f'{len(public_buckets)} bucket(s) without public access block' if public_buckets else 'All buckets block public access',
                'Recommendation': f'Enable public access block on: {", ".join([b.get("Name") for b in public_buckets[:3]])}' if public_buckets else 'Compliant'
            })
        else:
            results['checks'].append({
                'BenchmarkID': 'CIS-2.1.3',
                'Resource': 'S3 Public Access Block',
                'Status': 'NOT_VERIFIED',
                'Severity': 'INFO',
                'Finding': 'No S3 bucket data available',
                'Recommendation': 'Collect S3 bucket data'
            })
        
        # CIS 2.1.4: Ensure S3 bucket versioning is enabled
        if buckets:
            no_versioning = [b for b in buckets if not b.get('Versioning', {}).get('Status') == 'Enabled']
            results['checks'].append({
                'BenchmarkID': 'CIS-2.1.4',
                'Resource': 'S3 Bucket Versioning',
                'Status': 'FAIL' if no_versioning else 'PASS',
                'Severity': 'MEDIUM' if no_versioning else 'INFO',
                'Finding': f'{len(no_versioning)} bucket(s) without versioning' if no_versioning else 'All buckets have versioning',
                'Recommendation': f'Enable versioning on: {", ".join([b.get("Name") for b in no_versioning[:3]])}' if no_versioning else 'Compliant'
            })
        else:
            results['checks'].append({
                'BenchmarkID': 'CIS-2.1.4',
                'Resource': 'S3 Bucket Versioning',
                'Status': 'NOT_VERIFIED',
                'Severity': 'INFO',
                'Finding': 'No S3 bucket data available',
                'Recommendation': 'Collect S3 bucket data'
            })
        
        # CIS 2.1.5: Ensure S3 buckets have MFA Delete enabled
        results['checks'].append({
            'BenchmarkID': 'CIS-2.1.5',
            'Resource': 'S3 MFA Delete',
            'Status': 'NOT_VERIFIED',
            'Severity': 'INFO',
            'Finding': 'MFA Delete requires root account credentials to verify',
            'Recommendation': 'Manually verify MFA Delete is enabled on critical buckets'
        })
        
        # CIS 2.2.1: Ensure EBS volume encryption is enabled
        results['checks'].append({
            'BenchmarkID': 'CIS-2.2.1',
            'Resource': 'EBS Volume Encryption',
            'Status': 'NOT_VERIFIED',
            'Severity': 'INFO',
            'Finding': 'EBS encryption data not collected',
            'Recommendation': 'Add EBS volume encryption verification'
        })
        
        # CIS 2.3.1: Ensure RDS encryption is enabled
        rds_data = self.collected_data.get('RDS', {})
        instances = rds_data.get('Instances', [])
        if instances:
            unencrypted_rds = [i for i in instances if not i.get('StorageEncrypted')]
            results['checks'].append({
                'BenchmarkID': 'CIS-2.3.1',
                'Resource': 'RDS Encryption',
                'Status': 'FAIL' if unencrypted_rds else 'PASS',
                'Severity': 'HIGH' if unencrypted_rds else 'INFO',
                'Finding': f'{len(unencrypted_rds)} RDS instance(s) without encryption' if unencrypted_rds else 'All RDS instances encrypted',
                'Recommendation': f'Enable encryption on: {", ".join([i.get("DBInstanceIdentifier") for i in unencrypted_rds[:3]])}' if unencrypted_rds else 'Compliant'
            })
        else:
            results['checks'].append({
                'BenchmarkID': 'CIS-2.3.1',
                'Resource': 'RDS Encryption',
                'Status': 'NOT_VERIFIED',
                'Severity': 'INFO',
                'Finding': 'No RDS instances found or data not collected',
                'Recommendation': 'N/A - No RDS instances'
            })
        
        # CIS 2.3.2: Ensure auto minor version upgrade is enabled
        if instances:
            no_auto_upgrade = [i for i in instances if not i.get('AutoMinorVersionUpgrade')]
            results['checks'].append({
                'BenchmarkID': 'CIS-2.3.2',
                'Resource': 'RDS Auto Minor Version Upgrade',
                'Status': 'FAIL' if no_auto_upgrade else 'PASS',
                'Severity': 'MEDIUM' if no_auto_upgrade else 'INFO',
                'Finding': f'{len(no_auto_upgrade)} RDS instance(s) without auto upgrade' if no_auto_upgrade else 'All RDS instances have auto upgrade',
                'Recommendation': f'Enable auto upgrade on: {", ".join([i.get("DBInstanceIdentifier") for i in no_auto_upgrade[:3]])}' if no_auto_upgrade else 'Compliant'
            })
        else:
            results['checks'].append({
                'BenchmarkID': 'CIS-2.3.2',
                'Resource': 'RDS Auto Minor Version Upgrade',
                'Status': 'NOT_VERIFIED',
                'Severity': 'INFO',
                'Finding': 'No RDS instances found or data not collected',
                'Recommendation': 'N/A - No RDS instances'
            })
        
        # ====================
        # SECTION 3: Logging
        # ====================
        
        # CIS 3.1: Ensure CloudTrail is enabled in all regions
        cloudtrail = security_audit.get('CloudTrail', {})
        trails = cloudtrail.get('Trails', [])
        multi_region_trails = [t for t in trails if t.get('IsMultiRegionTrail') and t.get('IsLogging')]
        
        results['checks'].append({
            'BenchmarkID': 'CIS-3.1',
            'Resource': 'CloudTrail Multi-Region',
            'Status': 'PASS' if multi_region_trails else 'FAIL',
            'Severity': 'CRITICAL' if not multi_region_trails else 'INFO',
            'Finding': f'{len(multi_region_trails)} multi-region trail(s) active' if multi_region_trails else 'No multi-region CloudTrail enabled',
            'Recommendation': '🔒 CRITICAL: Enable CloudTrail in all regions' if not multi_region_trails else 'Compliant'
        })
        
        # CIS 3.2: Ensure CloudTrail log file validation is enabled
        if trails:
            no_validation = [t for t in trails if not t.get('LogFileValidationEnabled')]
            results['checks'].append({
                'BenchmarkID': 'CIS-3.2',
                'Resource': 'CloudTrail Log Validation',
                'Status': 'FAIL' if no_validation else 'PASS',
                'Severity': 'MEDIUM' if no_validation else 'INFO',
                'Finding': f'{len(no_validation)} trail(s) without log validation' if no_validation else 'All trails have log validation',
                'Recommendation': 'Enable log file validation on all trails' if no_validation else 'Compliant'
            })
        else:
            results['checks'].append({
                'BenchmarkID': 'CIS-3.2',
                'Resource': 'CloudTrail Log Validation',
                'Status': 'FAIL',
                'Severity': 'CRITICAL',
                'Finding': 'No CloudTrail trails configured',
                'Recommendation': 'Enable CloudTrail with log validation'
            })
        
        # CIS 3.3: Ensure S3 bucket used for CloudTrail logging is not publicly accessible
        results['checks'].append({
            'BenchmarkID': 'CIS-3.3',
            'Resource': 'CloudTrail S3 Bucket Access',
            'Status': 'NOT_VERIFIED',
            'Severity': 'INFO',
            'Finding': 'Requires cross-referencing CloudTrail bucket with S3 public access',
            'Recommendation': 'Verify CloudTrail S3 buckets are not publicly accessible'
        })
        
        # CIS 3.4: Ensure CloudTrail trails are integrated with CloudWatch Logs
        if trails:
            no_cloudwatch = [t for t in trails if not t.get('CloudWatchLogsLogGroupArn')]
            results['checks'].append({
                'BenchmarkID': 'CIS-3.4',
                'Resource': 'CloudTrail CloudWatch Integration',
                'Status': 'FAIL' if no_cloudwatch else 'PASS',
                'Severity': 'MEDIUM' if no_cloudwatch else 'INFO',
                'Finding': f'{len(no_cloudwatch)} trail(s) not integrated with CloudWatch' if no_cloudwatch else 'All trails integrated with CloudWatch',
                'Recommendation': 'Integrate CloudTrail with CloudWatch Logs' if no_cloudwatch else 'Compliant'
            })
        else:
            results['checks'].append({
                'BenchmarkID': 'CIS-3.4',
                'Resource': 'CloudTrail CloudWatch Integration',
                'Status': 'FAIL',
                'Severity': 'MEDIUM',
                'Finding': 'No CloudTrail trails configured',
                'Recommendation': 'Enable CloudTrail with CloudWatch integration'
            })
        
        # CIS 3.5: Ensure AWS Config is enabled in all regions
        aws_config = security_audit.get('AWSConfig', {})
        results['checks'].append({
            'BenchmarkID': 'CIS-3.5',
            'Resource': 'AWS Config',
            'Status': 'PASS' if aws_config.get('Enabled') else 'FAIL',
            'Severity': 'MEDIUM' if not aws_config.get('Enabled') else 'INFO',
            'Finding': 'AWS Config enabled' if aws_config.get('Enabled') else 'AWS Config not enabled',
            'Recommendation': '🔒 MEDIUM: Enable AWS Config in all regions' if not aws_config.get('Enabled') else 'Compliant'
        })
        
        # CIS 3.6: Ensure S3 bucket access logging is enabled on CloudTrail S3 bucket
        results['checks'].append({
            'BenchmarkID': 'CIS-3.6',
            'Resource': 'CloudTrail Bucket Logging',
            'Status': 'NOT_VERIFIED',
            'Severity': 'INFO',
            'Finding': 'Requires verification of CloudTrail bucket logging',
            'Recommendation': 'Verify S3 access logging is enabled on CloudTrail buckets'
        })
        
        # CIS 3.7: Ensure VPC flow logging is enabled in all VPCs
        vpc_flow = security_audit.get('VPCFlowLogs', {})
        total_vpcs = vpc_flow.get('TotalVPCs', 0)
        vpcs_with_logs = vpc_flow.get('VPCsWithFlowLogs', 0)
        
        if total_vpcs > 0:
            results['checks'].append({
                'BenchmarkID': 'CIS-3.7',
                'Resource': 'VPC Flow Logs',
                'Status': 'PASS' if total_vpcs == vpcs_with_logs else 'FAIL',
                'Severity': 'MEDIUM' if total_vpcs != vpcs_with_logs else 'INFO',
                'Finding': f'{vpcs_with_logs}/{total_vpcs} VPCs have flow logging' if total_vpcs != vpcs_with_logs else 'All VPCs have flow logging',
                'Recommendation': f'Enable flow logs on {total_vpcs - vpcs_with_logs} VPC(s)' if total_vpcs != vpcs_with_logs else 'Compliant'
            })
        else:
            results['checks'].append({
                'BenchmarkID': 'CIS-3.7',
                'Resource': 'VPC Flow Logs',
                'Status': 'NOT_VERIFIED',
                'Severity': 'INFO',
                'Finding': 'No VPC data available',
                'Recommendation': 'Collect VPC data'
            })
        
        # CIS 3.8-3.11: CloudWatch metric filters and alarms
        for check_id, check_name in [
            ('3.8', 'Unauthorized API Calls'),
            ('3.9', 'Management Console Sign-in Without MFA'),
            ('3.10', 'Root Account Usage'),
            ('3.11', 'IAM Policy Changes')
        ]:
            results['checks'].append({
                'BenchmarkID': f'CIS-{check_id}',
                'Resource': f'CloudWatch Alarm - {check_name}',
                'Status': 'NOT_VERIFIED',
                'Severity': 'INFO',
                'Finding': 'CloudWatch metric filter and alarm verification not implemented',
                'Recommendation': f'Create metric filter and alarm for {check_name.lower()}'
            })
        
        # ====================
        # SECTION 4: Monitoring
        # ====================
        
        # CIS 4.1-4.15: Additional CloudWatch metric filters
        monitoring_checks = [
            ('4.1', 'Unauthorized API calls'),
            ('4.2', 'Management Console sign-in without MFA'),
            ('4.3', 'Root account usage'),
            ('4.4', 'IAM policy changes'),
            ('4.5', 'CloudTrail configuration changes'),
            ('4.6', 'AWS Management Console authentication failures'),
            ('4.7', 'Disabling or scheduled deletion of CMKs'),
            ('4.8', 'S3 bucket policy changes'),
            ('4.9', 'AWS Config configuration changes'),
            ('4.10', 'Security group changes'),
            ('4.11', 'Network Access Control List (NACL) changes'),
            ('4.12', 'Changes to network gateways'),
            ('4.13', 'Route table changes'),
            ('4.14', 'VPC changes'),
            ('4.15', 'AWS Organizations changes')
        ]
        
        for check_id, check_desc in monitoring_checks:
            results['checks'].append({
                'BenchmarkID': f'CIS-{check_id}',
                'Resource': f'Metric Filter/Alarm - {check_desc}',
                'Status': 'NOT_VERIFIED',
                'Severity': 'INFO',
                'Finding': 'CloudWatch monitoring not fully implemented',
                'Recommendation': f'Implement metric filter and alarm for {check_desc}'
            })
        
        return results
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive verification report"""
        report = {
            'AccountId': self.collected_data.get('AccountId'),
            'Region': self.collected_data.get('Region'),
            'CollectionTimestamp': self.collected_data.get('CollectionTimestamp'),
            'VerificationTimestamp': json.dumps(Path(__file__).stat().st_mtime),
            'CollectedData': self.collected_data,  # Include raw collected data for HTML generator
            'Sections': []
        }
        
        # Run all verifications
        verifications = [
            self.verify_vpc_architecture,
            self.verify_security_groups,
            self.verify_compute_resources,
            self.verify_databases,
            self.verify_load_balancers,
            self.verify_storage,
            self.verify_iam,
            self.verify_monitoring,
            self.verify_bedrock,
            self.verify_sagemaker,
            self.verify_cis_benchmarks
        ]
        
        for verify_func in verifications:
            try:
                result = verify_func()
                report['Sections'].append(result)
            except Exception as e:
                report['Sections'].append({
                    'title': verify_func.__name__,
                    'error': str(e)
                })
        
        return report


def main():
    parser = argparse.ArgumentParser(description='AWS Build Review Verification')
    parser.add_argument('--collected-data', required=True, help='Path to collected AWS data JSON file')
    parser.add_argument('--design-spec', help='Path to design specification JSON file (optional)')
    parser.add_argument('--output', help='Output file path', default='verification_report.json')
    
    args = parser.parse_args()
    
    try:
        verifier = BuildVerifier(args.collected_data, args.design_spec)
        report = verifier.generate_report()
        
        # Save report
        output_path = Path(args.output)
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"Verification report generated: {output_path}")
        
        # Print summary
        print("\n=== Verification Summary ===")
        print(f"Account: {report.get('AccountId')}")
        print(f"Region: {report.get('Region')}")
        print(f"Sections Verified: {len(report.get('Sections', []))}")
        
    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == '__main__':
    main()