#!/usr/bin/env python3
"""
AWS Build Review Data Collection Script
Collects comprehensive AWS infrastructure information for verification against HLDs and detailed designs
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
                    
                bucket_data.append({
                    'Name': bucket_name,
                    'CreationDate': bucket['CreationDate'].isoformat(),
                    'Location': location,
                    'Versioning': versioning,
                    'Encryption': encryption,
                    'Policy': policy,
                    'PublicAccessBlock': public_access_block,
                    'Logging': logging
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
            ('Route53', self.get_route53_configuration),
            ('ElastiCache', self.get_elasticache_configuration),
            ('ECS', self.get_ecs_configuration),
            ('EKS', self.get_eks_configuration),
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
