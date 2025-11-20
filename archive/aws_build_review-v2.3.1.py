#!/usr/bin/env python3
"""
AWS Build Review Data Collection Script
Version: 2.3.1
Collects comprehensive AWS infrastructure information for verification against HLDs and detailed designs

Changelog:
- v2.3.1: Added VPC Endpoints collection to VPC configuration
- v2.3.0: Initial stable release with comprehensive AWS service coverage
"""

import boto3
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import sys

class AWSBuildReviewer:
    def __init__(self, profile: str = None, region: str = None):
        """Initialize AWS session with optional profile and region"""
        session_args = {}
        if profile:
            session_args['profile_name'] = profile
        if region:
            session_args['region_name'] = region
        
        self.session = boto3.Session(**session_args)
        self.account_id = self.session.client('sts').get_caller_identity()['Account']
        self.region = self.session.region_name or 'us-east-1'
        
    def get_vpc_configuration(self) -> Dict[str, Any]:
        """Collect VPC configuration including subnets, route tables, NACLs, and IGWs"""
        ec2 = self.session.client('ec2')
        
        vpcs = ec2.describe_vpcs()['Vpcs']
        vpc_data = []
        
        for vpc in vpcs:
            vpc_id = vpc['VpcId']
            
            # Get subnets
            subnets = ec2.describe_subnets(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])['Subnets']
            
            # Get route tables
            route_tables = ec2.describe_route_tables(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])['RouteTables']
            
            # Get NACLs
            nacls = ec2.describe_network_acls(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])['NetworkAcls']
            
            # Get Internet Gateways
            igws = ec2.describe_internet_gateways(Filters=[{'Name': 'attachment.vpc-id', 'Values': [vpc_id]}])['InternetGateways']
            
            # Get NAT Gateways
            nat_gws = ec2.describe_nat_gateways(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])['NatGateways']
            
            # Get VPC Endpoints
            vpc_endpoints = ec2.describe_vpc_endpoints(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])['VpcEndpoints']
            
            # Get VPC Peering Connections
            peering = ec2.describe_vpc_peering_connections(
                Filters=[
                    {'Name': 'requester-vpc-info.vpc-id', 'Values': [vpc_id]},
                ]
            )['VpcPeeringConnections']
            
            vpc_data.append({
                'VpcId': vpc_id,
                'CidrBlock': vpc.get('CidrBlock'),
                'CidrBlockAssociationSet': vpc.get('CidrBlockAssociationSet', []),
                'IsDefault': vpc.get('IsDefault'),
                'DhcpOptionsId': vpc.get('DhcpOptionsId'),
                'Tags': vpc.get('Tags', []),
                'Subnets': subnets,
                'RouteTables': route_tables,
                'NetworkACLs': nacls,
                'InternetGateways': igws,
                'NatGateways': nat_gws,
                'VpcEndpoints': vpc_endpoints,
                'VpcPeeringConnections': peering
            })
            
        return {'VPCs': vpc_data}
    
    def get_security_groups(self) -> Dict[str, Any]:
        """Collect all security groups and their rules"""
        ec2 = self.session.client('ec2')
        security_groups = ec2.describe_security_groups()['SecurityGroups']
        return {'SecurityGroups': security_groups}
    
    def get_ec2_instances(self) -> Dict[str, Any]:
        """Collect EC2 instance configurations"""
        ec2 = self.session.client('ec2')
        
        instances = ec2.describe_instances()
        instance_data = []
        
        for reservation in instances['Reservations']:
            for instance in reservation['Instances']:
                instance_data.append(instance)
        
        # Get AMI details
        if instance_data:
            ami_ids = list(set([i['ImageId'] for i in instance_data if 'ImageId' in i]))
            amis = ec2.describe_images(ImageIds=ami_ids) if ami_ids else {'Images': []}
        else:
            amis = {'Images': []}
            
        return {
            'Instances': instance_data,
            'AMIs': amis['Images']
        }
    
    def get_load_balancers(self) -> Dict[str, Any]:
        """Collect ALB/NLB configurations"""
        elbv2 = self.session.client('elbv2')
        
        load_balancers = elbv2.describe_load_balancers().get('LoadBalancers', [])
        lb_data = []
        
        for lb in load_balancers:
            lb_arn = lb['LoadBalancerArn']
            
            # Get listeners
            listeners = elbv2.describe_listeners(LoadBalancerArn=lb_arn).get('Listeners', [])
            
            # Get target groups
            target_groups = elbv2.describe_target_groups(LoadBalancerArn=lb_arn).get('TargetGroups', [])
            
            # Get targets for each target group
            for tg in target_groups:
                tg_arn = tg['TargetGroupArn']
                targets = elbv2.describe_target_health(TargetGroupArn=tg_arn).get('TargetHealthDescriptions', [])
                tg['Targets'] = targets
            
            lb_data.append({
                'LoadBalancer': lb,
                'Listeners': listeners,
                'TargetGroups': target_groups
            })
            
        return {'LoadBalancers': lb_data}
    
    def get_rds_databases(self) -> Dict[str, Any]:
        """Collect RDS instance and cluster configurations"""
        rds = self.session.client('rds')
        
        db_instances = rds.describe_db_instances().get('DBInstances', [])
        db_clusters = rds.describe_db_clusters().get('DBClusters', [])
        db_subnet_groups = rds.describe_db_subnet_groups().get('DBSubnetGroups', [])
        db_parameter_groups = rds.describe_db_parameter_groups().get('DBParameterGroups', [])
        
        return {
            'DBInstances': db_instances,
            'DBClusters': db_clusters,
            'DBSubnetGroups': db_subnet_groups,
            'DBParameterGroups': db_parameter_groups
        }
    
    def get_s3_buckets(self) -> Dict[str, Any]:
        """Collect S3 bucket configurations"""
        s3 = self.session.client('s3')
        
        buckets = s3.list_buckets().get('Buckets', [])
        bucket_data = []
        
        for bucket in buckets:
            bucket_name = bucket['Name']
            
            try:
                # Get bucket location
                location = s3.get_bucket_location(Bucket=bucket_name)
                
                # Get bucket versioning
                versioning = s3.get_bucket_versioning(Bucket=bucket_name)
                
                # Get bucket encryption
                try:
                    encryption = s3.get_bucket_encryption(Bucket=bucket_name)
                except:
                    encryption = None
                
                # Get bucket policy
                try:
                    policy = s3.get_bucket_policy(Bucket=bucket_name)
                except:
                    policy = None
                
                # Get public access block
                try:
                    public_access_block = s3.get_public_access_block(Bucket=bucket_name)
                except:
                    public_access_block = None
                
                # Get bucket logging
                try:
                    logging = s3.get_bucket_logging(Bucket=bucket_name)
                except:
                    logging = None
                
                # Get bucket tagging
                try:
                    tagging = s3.get_bucket_tagging(Bucket=bucket_name)
                except:
                    tagging = None
                    
                bucket_data.append({
                    'Name': bucket_name,
                    'CreationDate': bucket['CreationDate'].isoformat(),
                    'Location': location,
                    'Versioning': versioning,
                    'Encryption': encryption,
                    'Policy': policy,
                    'PublicAccessBlock': public_access_block,
                    'Logging': logging,
                    'Tagging': tagging
                })
            except Exception as e:
                bucket_data.append({
                    'Name': bucket_name,
                    'Error': str(e)
                })
        
        return {'Buckets': bucket_data}
    
    def get_lambda_functions(self) -> Dict[str, Any]:
        """Collect Lambda function configurations"""
        lambda_client = self.session.client('lambda')
        
        functions = lambda_client.list_functions().get('Functions', [])
        function_data = []
        
        for func in functions:
            func_name = func['FunctionName']
            
            # Get function configuration
            config = lambda_client.get_function(FunctionName=func_name)
            
            # Get function policy
            try:
                policy = lambda_client.get_policy(FunctionName=func_name)
            except:
                policy = None
            
            function_data.append({
                'Configuration': config,
                'Policy': policy
            })
            
        return {'Functions': function_data}
    
    def get_iam_configuration(self) -> Dict[str, Any]:
        """Collect IAM roles, policies, and users"""
        iam = self.session.client('iam')
        
        roles = iam.list_roles().get('Roles', [])
        role_data = []
        
        for role in roles:
            role_name = role['RoleName']
            
            # Get attached policies
            attached_policies = iam.list_attached_role_policies(RoleName=role_name).get('AttachedPolicies', [])
            
            # Get inline policies
            inline_policies = iam.list_role_policies(RoleName=role_name).get('PolicyNames', [])
            inline_policy_docs = {}
            for policy_name in inline_policies:
                policy_doc = iam.get_role_policy(RoleName=role_name, PolicyName=policy_name)
                inline_policy_docs[policy_name] = policy_doc.get('PolicyDocument')
            
            role_data.append({
                'Role': role,
                'AttachedPolicies': attached_policies,
                'InlinePolicies': inline_policy_docs
            })
        
        # Get users
        users = iam.list_users().get('Users', [])
        
        # Get policies
        policies = iam.list_policies(Scope='Local').get('Policies', [])
        
        return {
            'Roles': role_data,
            'Users': users,
            'CustomerManagedPolicies': policies
        }
    
    def get_cloudwatch_configuration(self) -> Dict[str, Any]:
        """Collect CloudWatch alarms and log groups"""
        cloudwatch = self.session.client('cloudwatch')
        logs = self.session.client('logs')
        
        alarms = cloudwatch.describe_alarms().get('MetricAlarms', [])
        log_groups = logs.describe_log_groups().get('logGroups', [])
        
        return {
            'Alarms': alarms,
            'LogGroups': log_groups
        }
    
    def get_security_audit_configuration(self) -> Dict[str, Any]:
        """
        Collect security audit configurations for CIS Benchmark compliance
        
        Required IAM Permissions:
        - cloudtrail:DescribeTrails
        - cloudtrail:GetTrailStatus
        - cloudtrail:GetEventSelectors
        - ec2:DescribeFlowLogs
        - ec2:DescribeVpcs
        - iam:GetAccountPasswordPolicy
        - iam:GetAccountSummary
        - iam:GenerateCredentialReport
        - iam:GetCredentialReport
        - iam:ListAccessKeys
        - iam:ListMFADevices
        - iam:ListVirtualMFADevices
        - s3:GetBucketVersioning
        - s3:GetBucketLogging
        - s3:GetBucketPolicy
        - kms:DescribeKey
        - kms:GetKeyRotationStatus
        - config:DescribeConfigurationRecorders
        - config:DescribeConfigurationRecorderStatus
        - access-analyzer:ListAnalyzers
        """
        try:
            data = {
                'CloudTrail': {},
                'VPCFlowLogs': {},
                'IAMPasswordPolicy': {},
                'IAMCredentialReport': {},
                'RootAccountChecks': {},
                'AWSConfig': {},
                'IAMAccessAnalyzer': {},
                'Errors': []
            }
            
            # CloudTrail Configuration (CIS 3.1-3.4)
            try:
                cloudtrail = self.session.client('cloudtrail')
                trails = cloudtrail.describe_trails().get('trailList', [])
                
                trail_details = []
                for trail in trails:
                    trail_arn = trail.get('TrailARN')
                    trail_name = trail.get('Name')
                    
                    try:
                        # Get trail status
                        status = cloudtrail.get_trail_status(Name=trail_name)
                        
                        # Get event selectors
                        event_selectors = cloudtrail.get_event_selectors(TrailName=trail_name)
                        
                        trail_details.append({
                            'Trail': trail,
                            'Status': status,
                            'EventSelectors': event_selectors,
                            'IsLogging': status.get('IsLogging', False),
                            'IsMultiRegionTrail': trail.get('IsMultiRegionTrail', False),
                            'LogFileValidationEnabled': trail.get('LogFileValidationEnabled', False),
                            'S3BucketName': trail.get('S3BucketName'),
                            'CloudWatchLogsLogGroupArn': trail.get('CloudWatchLogsLogGroupArn')
                        })
                    except Exception as e:
                        data['Errors'].append(f"GetTrailStatus/EventSelectors {trail_name}: {str(e)}")
                
                data['CloudTrail'] = {
                    'Trails': trail_details,
                    'TrailCount': len(trail_details)
                }
            except Exception as e:
                data['Errors'].append(f"CloudTrail collection: {str(e)}")
            
            # VPC Flow Logs (CIS 3.7)
            try:
                ec2 = self.session.client('ec2')
                vpcs = ec2.describe_vpcs().get('Vpcs', [])
                flow_logs = ec2.describe_flow_logs().get('FlowLogs', [])
                
                vpc_flow_log_status = []
                for vpc in vpcs:
                    vpc_id = vpc.get('VpcId')
                    vpc_flow_logs = [fl for fl in flow_logs if fl.get('ResourceId') == vpc_id]
                    
                    vpc_flow_log_status.append({
                        'VpcId': vpc_id,
                        'FlowLogsEnabled': len(vpc_flow_logs) > 0,
                        'FlowLogs': vpc_flow_logs
                    })
                
                data['VPCFlowLogs'] = {
                    'VPCs': vpc_flow_log_status,
                    'TotalVPCs': len(vpcs),
                    'VPCsWithFlowLogs': sum(1 for v in vpc_flow_log_status if v['FlowLogsEnabled'])
                }
            except Exception as e:
                data['Errors'].append(f"VPC Flow Logs collection: {str(e)}")
            
            # IAM Password Policy (CIS 1.5-1.11)
            try:
                iam = self.session.client('iam')
                try:
                    password_policy = iam.get_account_password_policy()
                    data['IAMPasswordPolicy'] = {
                        'Exists': True,
                        'Policy': password_policy.get('PasswordPolicy', {})
                    }
                except iam.exceptions.NoSuchEntityException:
                    data['IAMPasswordPolicy'] = {
                        'Exists': False,
                        'Policy': {}
                    }
            except Exception as e:
                data['Errors'].append(f"IAM Password Policy: {str(e)}")
            
            # IAM Credential Report (CIS 1.4, 1.12-1.15)
            try:
                iam = self.session.client('iam')
                
                # Generate credential report
                try:
                    iam.generate_credential_report()
                    
                    # Wait a moment for generation
                    import time
                    time.sleep(2)
                    
                    # Get credential report
                    report_response = iam.get_credential_report()
                    report_content = report_response.get('Content', b'').decode('utf-8')
                    
                    # Parse CSV report
                    import csv
                    import io
                    reader = csv.DictReader(io.StringIO(report_content))
                    credentials = list(reader)
                    
                    # Analyze root account
                    root_user = next((c for c in credentials if c.get('user') == '<root_account>'), None)
                    
                    # Analyze regular users
                    regular_users = [c for c in credentials if c.get('user') != '<root_account>']
                    
                    data['IAMCredentialReport'] = {
                        'RootUser': root_user,
                        'Users': regular_users,
                        'TotalUsers': len(regular_users)
                    }
                    
                    # Root account specific checks
                    if root_user:
                        data['RootAccountChecks'] = {
                            'AccessKey1Active': root_user.get('access_key_1_active', 'false').lower() == 'true',
                            'AccessKey2Active': root_user.get('access_key_2_active', 'false').lower() == 'true',
                            'MFAActive': root_user.get('mfa_active', 'false').lower() == 'true',
                            'PasswordLastUsed': root_user.get('password_last_used', 'N/A')
                        }
                    
                except Exception as e:
                    data['Errors'].append(f"Credential Report generation/retrieval: {str(e)}")
                
                # Get MFA devices
                try:
                    virtual_mfa = iam.list_virtual_mfa_devices()
                    data['IAMCredentialReport']['VirtualMFADevices'] = virtual_mfa.get('VirtualMFADevices', [])
                except Exception as e:
                    data['Errors'].append(f"List Virtual MFA Devices: {str(e)}")
                
            except Exception as e:
                data['Errors'].append(f"IAM Credential Report: {str(e)}")
            
            # AWS Config (CIS 3.5)
            try:
                config = self.session.client('config')
                
                recorders = config.describe_configuration_recorders().get('ConfigurationRecorders', [])
                recorder_status = []
                
                for recorder in recorders:
                    try:
                        status = config.describe_configuration_recorder_status(
                            ConfigurationRecorderNames=[recorder.get('name')]
                        )
                        recorder_status.append({
                            'Recorder': recorder,
                            'Status': status.get('ConfigurationRecordersStatus', [{}])[0]
                        })
                    except Exception as e:
                        data['Errors'].append(f"Config Recorder Status: {str(e)}")
                
                data['AWSConfig'] = {
                    'Recorders': recorder_status,
                    'Enabled': len([r for r in recorder_status if r.get('Status', {}).get('recording', False)]) > 0
                }
            except Exception as e:
                data['Errors'].append(f"AWS Config collection: {str(e)}")
            
            # IAM Access Analyzer
            try:
                access_analyzer = self.session.client('accessanalyzer')
                analyzers = access_analyzer.list_analyzers().get('analyzers', [])
                
                data['IAMAccessAnalyzer'] = {
                    'Analyzers': analyzers,
                    'Enabled': len([a for a in analyzers if a.get('status') == 'ACTIVE']) > 0
                }
            except Exception as e:
                data['Errors'].append(f"IAM Access Analyzer: {str(e)}")
            
            return data
            
        except Exception as e:
            return {'Error': str(e), 'Errors': [str(e)]}
    
    def get_route53_configuration(self) -> Dict[str, Any]:
        """Collect Route53 hosted zones and records"""
        route53 = self.session.client('route53')
        
        hosted_zones = route53.list_hosted_zones().get('HostedZones', [])
        zone_data = []
        
        for zone in hosted_zones:
            zone_id = zone['Id']
            
            # Get record sets
            record_sets = route53.list_resource_record_sets(HostedZoneId=zone_id).get('ResourceRecordSets', [])
            
            zone_data.append({
                'HostedZone': zone,
                'RecordSets': record_sets
            })
        
        return {'HostedZones': zone_data}
    
    def get_elasticache_configuration(self) -> Dict[str, Any]:
        """Collect ElastiCache cluster configurations"""
        elasticache = self.session.client('elasticache')
        
        cache_clusters = elasticache.describe_cache_clusters(ShowCacheNodeInfo=True).get('CacheClusters', [])
        replication_groups = elasticache.describe_replication_groups().get('ReplicationGroups', [])
        
        return {
            'CacheClusters': cache_clusters,
            'ReplicationGroups': replication_groups
        }
    
    def get_ecs_configuration(self) -> Dict[str, Any]:
        """Collect ECS cluster, service, and task configurations"""
        ecs = self.session.client('ecs')
        
        cluster_arns = ecs.list_clusters().get('clusterArns', [])
        cluster_data = []
        
        for cluster_arn in cluster_arns:
            # Get cluster details
            clusters = ecs.describe_clusters(clusters=[cluster_arn]).get('clusters', [])
            
            if clusters:
                cluster = clusters[0]
                
                # Get services
                service_arns = ecs.list_services(cluster=cluster_arn).get('serviceArns', [])
                services = []
                if service_arns:
                    services = ecs.describe_services(cluster=cluster_arn, services=service_arns).get('services', [])
                
                # Get task definitions
                task_def_arns = ecs.list_task_definitions().get('taskDefinitionArns', [])
                
                cluster_data.append({
                    'Cluster': cluster,
                    'Services': services,
                    'TaskDefinitions': task_def_arns
                })
        
        return {'Clusters': cluster_data}
    
    def get_eks_configuration(self) -> Dict[str, Any]:
        """Collect EKS cluster configurations"""
        try:
            eks = self.session.client('eks')
            
            cluster_names = eks.list_clusters().get('clusters', [])
            cluster_data = []
            
            for cluster_name in cluster_names:
                cluster = eks.describe_cluster(name=cluster_name).get('cluster', {})
                
                # Get node groups
                nodegroup_names = eks.list_nodegroups(clusterName=cluster_name).get('nodegroups', [])
                nodegroups = []
                for ng_name in nodegroup_names:
                    ng = eks.describe_nodegroup(clusterName=cluster_name, nodegroupName=ng_name).get('nodegroup', {})
                    nodegroups.append(ng)
                
                cluster_data.append({
                    'Cluster': cluster,
                    'NodeGroups': nodegroups
                })
            
            return {'Clusters': cluster_data}
        except Exception as e:
            return {'Clusters': [], 'Error': str(e)}
    
    def get_bedrock_configuration(self) -> Dict[str, Any]:
        """
        Collect Amazon Bedrock configurations for security assessment
        
        Required IAM Permissions:
        - bedrock:ListFoundationModels
        - bedrock:GetFoundationModel
        - bedrock:ListModelCustomizationJobs
        - bedrock:GetModelCustomizationJob
        - bedrock:ListProvisionedModelThroughputs
        - bedrock:GetProvisionedModelThroughput
        - bedrock:ListGuardrails
        - bedrock:GetGuardrail
        - bedrock:ListCustomModels
        - bedrock:GetCustomModel
        - logs:DescribeLogGroups (for CloudWatch logging check)
        - iam:GetRole (for execution roles)
        - iam:GetRolePolicy
        - iam:ListAttachedRolePolicies
        - kms:DescribeKey (for encryption keys)
        """
        try:
            bedrock = self.session.client('bedrock')
            logs = self.session.client('logs')
            iam = self.session.client('iam')
            
            data = {
                'FoundationModels': [],
                'CustomModels': [],
                'ModelCustomizationJobs': [],
                'ProvisionedThroughputs': [],
                'Guardrails': [],
                'LoggingConfiguration': {},
                'Errors': []
            }
            
            # Get foundation models (available models)
            try:
                models_response = bedrock.list_foundation_models()
                data['FoundationModels'] = models_response.get('modelSummaries', [])
            except Exception as e:
                data['Errors'].append(f"ListFoundationModels: {str(e)}")
            
            # Get custom models
            try:
                custom_models = bedrock.list_custom_models()
                for model_summary in custom_models.get('modelSummaries', []):
                    try:
                        model_detail = bedrock.get_custom_model(modelIdentifier=model_summary['modelArn'])
                        data['CustomModels'].append(model_detail)
                    except Exception as e:
                        data['Errors'].append(f"GetCustomModel {model_summary['modelArn']}: {str(e)}")
            except Exception as e:
                data['Errors'].append(f"ListCustomModels: {str(e)}")
            
            # Get model customization jobs (for training data security)
            try:
                jobs_response = bedrock.list_model_customization_jobs()
                for job_summary in jobs_response.get('modelCustomizationJobSummaries', []):
                    try:
                        job_detail = bedrock.get_model_customization_job(jobIdentifier=job_summary['jobArn'])
                        data['ModelCustomizationJobs'].append(job_detail)
                    except Exception as e:
                        data['Errors'].append(f"GetModelCustomizationJob {job_summary['jobArn']}: {str(e)}")
            except Exception as e:
                data['Errors'].append(f"ListModelCustomizationJobs: {str(e)}")
            
            # Get provisioned throughputs (for VPC endpoint usage)
            try:
                throughputs = bedrock.list_provisioned_model_throughputs()
                for throughput_summary in throughputs.get('provisionedModelSummaries', []):
                    try:
                        throughput_detail = bedrock.get_provisioned_model_throughput(
                            provisionedModelId=throughput_summary['provisionedModelArn']
                        )
                        data['ProvisionedThroughputs'].append(throughput_detail)
                    except Exception as e:
                        data['Errors'].append(f"GetProvisionedModelThroughput {throughput_summary['provisionedModelArn']}: {str(e)}")
            except Exception as e:
                data['Errors'].append(f"ListProvisionedModelThroughputs: {str(e)}")
            
            # Get guardrails (content filtering, PII detection)
            try:
                guardrails = bedrock.list_guardrails()
                for guardrail_summary in guardrails.get('guardrails', []):
                    try:
                        guardrail_detail = bedrock.get_guardrail(
                            guardrailIdentifier=guardrail_summary['id'],
                            guardrailVersion=guardrail_summary.get('version', 'DRAFT')
                        )
                        data['Guardrails'].append(guardrail_detail)
                    except Exception as e:
                        data['Errors'].append(f"GetGuardrail {guardrail_summary['id']}: {str(e)}")
            except Exception as e:
                data['Errors'].append(f"ListGuardrails: {str(e)}")
            
            # Check CloudWatch Logs configuration for Bedrock
            try:
                log_groups = logs.describe_log_groups(logGroupNamePrefix='/aws/bedrock')
                data['LoggingConfiguration'] = {
                    'LogGroups': log_groups.get('logGroups', []),
                    'LoggingEnabled': len(log_groups.get('logGroups', [])) > 0
                }
            except Exception as e:
                data['Errors'].append(f"DescribeLogGroups: {str(e)}")
            
            return data
            
        except Exception as e:
            return {'Error': str(e), 'Errors': [str(e)]}
    
    def get_sagemaker_configuration(self) -> Dict[str, Any]:
        """
        Collect Amazon SageMaker configurations for security assessment
        
        Required IAM Permissions:
        - sagemaker:ListDomains
        - sagemaker:DescribeDomain
        - sagemaker:ListUserProfiles
        - sagemaker:DescribeUserProfile
        - sagemaker:ListNotebookInstances
        - sagemaker:DescribeNotebookInstance
        - sagemaker:ListTrainingJobs
        - sagemaker:DescribeTrainingJob
        - sagemaker:ListEndpoints
        - sagemaker:DescribeEndpoint
        - sagemaker:ListEndpointConfigs
        - sagemaker:DescribeEndpointConfig
        - sagemaker:ListModels
        - sagemaker:DescribeModel
        - sagemaker:ListModelPackages
        - sagemaker:DescribeModelPackage
        - sagemaker:ListFeatureGroups
        - sagemaker:DescribeFeatureGroup
        - iam:GetRole (for execution roles)
        - iam:GetRolePolicy
        - iam:ListAttachedRolePolicies
        - kms:DescribeKey (for encryption keys)
        - ec2:DescribeVpcs (for VPC configuration)
        - ec2:DescribeSubnets (for subnet configuration)
        - ec2:DescribeSecurityGroups (for security groups)
        """
        try:
            sagemaker = self.session.client('sagemaker')
            
            data = {
                'Domains': [],
                'NotebookInstances': [],
                'TrainingJobs': [],
                'Endpoints': [],
                'EndpointConfigs': [],
                'Models': [],
                'ModelPackages': [],
                'FeatureGroups': [],
                'Errors': []
            }
            
            # Get SageMaker Studio Domains
            try:
                domains_response = sagemaker.list_domains()
                for domain_summary in domains_response.get('Domains', []):
                    try:
                        domain_detail = sagemaker.describe_domain(DomainId=domain_summary['DomainId'])
                        
                        # Get user profiles for this domain
                        user_profiles = []
                        try:
                            profiles_response = sagemaker.list_user_profiles(DomainIdEquals=domain_summary['DomainId'])
                            for profile_summary in profiles_response.get('UserProfiles', []):
                                try:
                                    profile_detail = sagemaker.describe_user_profile(
                                        DomainId=domain_summary['DomainId'],
                                        UserProfileName=profile_summary['UserProfileName']
                                    )
                                    user_profiles.append(profile_detail)
                                except Exception as e:
                                    data['Errors'].append(f"DescribeUserProfile {profile_summary['UserProfileName']}: {str(e)}")
                        except Exception as e:
                            data['Errors'].append(f"ListUserProfiles: {str(e)}")
                        
                        domain_detail['UserProfiles'] = user_profiles
                        data['Domains'].append(domain_detail)
                    except Exception as e:
                        data['Errors'].append(f"DescribeDomain {domain_summary['DomainId']}: {str(e)}")
            except Exception as e:
                data['Errors'].append(f"ListDomains: {str(e)}")
            
            # Get Notebook Instances
            try:
                notebooks_response = sagemaker.list_notebook_instances()
                for notebook_summary in notebooks_response.get('NotebookInstances', []):
                    try:
                        notebook_detail = sagemaker.describe_notebook_instance(
                            NotebookInstanceName=notebook_summary['NotebookInstanceName']
                        )
                        data['NotebookInstances'].append(notebook_detail)
                    except Exception as e:
                        data['Errors'].append(f"DescribeNotebookInstance {notebook_summary['NotebookInstanceName']}: {str(e)}")
            except Exception as e:
                data['Errors'].append(f"ListNotebookInstances: {str(e)}")
            
            # Get Training Jobs (last 100)
            try:
                training_jobs_response = sagemaker.list_training_jobs(MaxResults=100)
                for job_summary in training_jobs_response.get('TrainingJobSummaries', []):
                    try:
                        job_detail = sagemaker.describe_training_job(
                            TrainingJobName=job_summary['TrainingJobName']
                        )
                        data['TrainingJobs'].append(job_detail)
                    except Exception as e:
                        data['Errors'].append(f"DescribeTrainingJob {job_summary['TrainingJobName']}: {str(e)}")
            except Exception as e:
                data['Errors'].append(f"ListTrainingJobs: {str(e)}")
            
            # Get Endpoints
            try:
                endpoints_response = sagemaker.list_endpoints()
                for endpoint_summary in endpoints_response.get('Endpoints', []):
                    try:
                        endpoint_detail = sagemaker.describe_endpoint(
                            EndpointName=endpoint_summary['EndpointName']
                        )
                        data['Endpoints'].append(endpoint_detail)
                    except Exception as e:
                        data['Errors'].append(f"DescribeEndpoint {endpoint_summary['EndpointName']}: {str(e)}")
            except Exception as e:
                data['Errors'].append(f"ListEndpoints: {str(e)}")
            
            # Get Endpoint Configs
            try:
                configs_response = sagemaker.list_endpoint_configs()
                for config_summary in configs_response.get('EndpointConfigs', []):
                    try:
                        config_detail = sagemaker.describe_endpoint_config(
                            EndpointConfigName=config_summary['EndpointConfigName']
                        )
                        data['EndpointConfigs'].append(config_detail)
                    except Exception as e:
                        data['Errors'].append(f"DescribeEndpointConfig {config_summary['EndpointConfigName']}: {str(e)}")
            except Exception as e:
                data['Errors'].append(f"ListEndpointConfigs: {str(e)}")
            
            # Get Models
            try:
                models_response = sagemaker.list_models()
                for model_summary in models_response.get('Models', []):
                    try:
                        model_detail = sagemaker.describe_model(
                            ModelName=model_summary['ModelName']
                        )
                        data['Models'].append(model_detail)
                    except Exception as e:
                        data['Errors'].append(f"DescribeModel {model_summary['ModelName']}: {str(e)}")
            except Exception as e:
                data['Errors'].append(f"ListModels: {str(e)}")
            
            # Get Model Packages (Model Registry)
            try:
                packages_response = sagemaker.list_model_packages(MaxResults=100)
                for package_summary in packages_response.get('ModelPackageSummaryList', []):
                    try:
                        package_detail = sagemaker.describe_model_package(
                            ModelPackageName=package_summary['ModelPackageArn']
                        )
                        data['ModelPackages'].append(package_detail)
                    except Exception as e:
                        data['Errors'].append(f"DescribeModelPackage {package_summary['ModelPackageArn']}: {str(e)}")
            except Exception as e:
                data['Errors'].append(f"ListModelPackages: {str(e)}")
            
            # Get Feature Groups (Feature Store)
            try:
                feature_groups_response = sagemaker.list_feature_groups()
                for fg_summary in feature_groups_response.get('FeatureGroupSummaries', []):
                    try:
                        fg_detail = sagemaker.describe_feature_group(
                            FeatureGroupName=fg_summary['FeatureGroupName']
                        )
                        data['FeatureGroups'].append(fg_detail)
                    except Exception as e:
                        data['Errors'].append(f"DescribeFeatureGroup {fg_summary['FeatureGroupName']}: {str(e)}")
            except Exception as e:
                data['Errors'].append(f"ListFeatureGroups: {str(e)}")
            
            return data
            
        except Exception as e:
            return {'Error': str(e), 'Errors': [str(e)]}
    
    def collect_all_data(self) -> Dict[str, Any]:
        """Collect all AWS infrastructure data"""
        print(f"Collecting data for Account: {self.account_id}, Region: {self.region}")
        
        data = {
            'AccountId': self.account_id,
            'Region': self.region,
            'CollectionTimestamp': datetime.utcnow().isoformat(),
        }
        
        collections = [
            ('VPC', self.get_vpc_configuration),
            ('SecurityGroups', self.get_security_groups),
            ('EC2', self.get_ec2_instances),
            ('LoadBalancers', self.get_load_balancers),
            ('RDS', self.get_rds_databases),
            ('S3', self.get_s3_buckets),
            ('Lambda', self.get_lambda_functions),
            ('IAM', self.get_iam_configuration),
            ('CloudWatch', self.get_cloudwatch_configuration),
            ('SecurityAudit', self.get_security_audit_configuration),
            ('Route53', self.get_route53_configuration),
            ('ElastiCache', self.get_elasticache_configuration),
            ('ECS', self.get_ecs_configuration),
            ('EKS', self.get_eks_configuration),
            ('Bedrock', self.get_bedrock_configuration),
            ('SageMaker', self.get_sagemaker_configuration),
        ]
        
        for name, func in collections:
            try:
                print(f"Collecting {name} data...")
                data[name] = func()
            except Exception as e:
                print(f"Error collecting {name} data: {str(e)}")
                data[name] = {'Error': str(e)}
        
        return data


def main():
    parser = argparse.ArgumentParser(description='AWS Build Review Data Collection')
    parser.add_argument('--profile', help='AWS profile name', default=None)
    parser.add_argument('--region', help='AWS region', default=None)
    parser.add_argument('--output', help='Output file path', default='aws_build_review_output.json')
    
    args = parser.parse_args()
    
    try:
        reviewer = AWSBuildReviewer(profile=args.profile, region=args.region)
        data = reviewer.collect_all_data()
        
        # Save to file
        output_path = Path(args.output)
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        print(f"\nData collection complete. Output saved to: {output_path}")
        print(f"File size: {output_path.stat().st_size / 1024 / 1024:.2f} MB")
        
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
