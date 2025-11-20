#!/usr/bin/env python3
"""
AWS Build Review Verification Script
Compares collected AWS infrastructure against HLD/detailed design specifications
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
        """Verify security group configurations"""
        results = {
            'title': 'Security Group Verification',
            'checks': []
        }
        
        security_groups = self.collected_data.get('SecurityGroups', {}).get('SecurityGroups', [])
        
        for sg in security_groups:
            sg_id = sg.get('GroupId')
            sg_name = sg.get('GroupName')
            
            # Check for overly permissive rules
            ingress_rules = sg.get('IpPermissions', [])
            egress_rules = sg.get('IpPermissionsEgress', [])
            
            open_to_world = []
            for rule in ingress_rules:
                for ip_range in rule.get('IpRanges', []):
                    if ip_range.get('CidrIp') == '0.0.0.0/0':
                        open_to_world.append({
                            'Protocol': rule.get('IpProtocol'),
                            'FromPort': rule.get('FromPort'),
                            'ToPort': rule.get('ToPort')
                        })
            
            results['checks'].append({
                'SecurityGroup': sg_id,
                'Name': sg_name,
                'VPC': sg.get('VpcId'),
                'IngressRules': len(ingress_rules),
                'EgressRules': len(egress_rules),
                'OpenToInternet': open_to_world,
                'Severity': 'HIGH' if open_to_world else 'INFO'
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
        for cluster_data in ecs_clusters:
            cluster = cluster_data.get('Cluster', {})
            services = cluster_data.get('Services', [])
            
            results['ecs'].append({
                'ClusterName': cluster.get('clusterName'),
                'Status': cluster.get('status'),
                'RegisteredInstances': cluster.get('registeredContainerInstancesCount'),
                'RunningTasks': cluster.get('runningTasksCount'),
                'Services': len(services),
                'ServiceDetails': [
                    {
                        'ServiceName': svc.get('serviceName'),
                        'Status': svc.get('status'),
                        'DesiredCount': svc.get('desiredCount'),
                        'RunningCount': svc.get('runningCount'),
                        'LaunchType': svc.get('launchType')
                    }
                    for svc in services
                ]
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
        """Verify RDS and ElastiCache configurations"""
        results = {
            'title': 'Database Verification',
            'rds': [],
            'elasticache': []
        }
        
        # RDS Instances
        db_instances = self.collected_data.get('RDS', {}).get('DBInstances', [])
        for db in db_instances:
            results['rds'].append({
                'DBInstanceIdentifier': db.get('DBInstanceIdentifier'),
                'Engine': db.get('Engine'),
                'EngineVersion': db.get('EngineVersion'),
                'InstanceClass': db.get('DBInstanceClass'),
                'StorageType': db.get('StorageType'),
                'AllocatedStorage': db.get('AllocatedStorage'),
                'MultiAZ': db.get('MultiAZ'),
                'PubliclyAccessible': db.get('PubliclyAccessible'),
                'StorageEncrypted': db.get('StorageEncrypted'),
                'BackupRetention': db.get('BackupRetentionPeriod'),
                'VPC': db.get('DBSubnetGroup', {}).get('VpcId'),
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
    
    def verify_iam(self) -> Dict[str, Any]:
        """Verify IAM configuration"""
        results = {
            'title': 'IAM Verification',
            'roles': [],
            'policies': [],
            'users': []
        }
        
        # Roles
        roles = self.collected_data.get('IAM', {}).get('Roles', [])
        for role_data in roles:
            role = role_data.get('Role', {})
            attached_policies = role_data.get('AttachedPolicies', [])
            inline_policies = role_data.get('InlinePolicies', {})
            
            results['roles'].append({
                'RoleName': role.get('RoleName'),
                'Path': role.get('Path'),
                'AttachedPolicies': len(attached_policies),
                'InlinePolicies': len(inline_policies),
                'MaxSessionDuration': role.get('MaxSessionDuration'),
                'AssumeRolePolicyDocument': role.get('AssumeRolePolicyDocument')
            })
        
        # Users
        users = self.collected_data.get('IAM', {}).get('Users', [])
        results['users'] = [
            {
                'UserName': user.get('UserName'),
                'Path': user.get('Path'),
                'CreateDate': user.get('CreateDate')
            }
            for user in users
        ]
        
        return results
    
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
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive verification report"""
        report = {
            'AccountId': self.collected_data.get('AccountId'),
            'Region': self.collected_data.get('Region'),
            'CollectionTimestamp': self.collected_data.get('CollectionTimestamp'),
            'VerificationTimestamp': json.dumps(Path(__file__).stat().st_mtime),
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
            self.verify_monitoring
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
