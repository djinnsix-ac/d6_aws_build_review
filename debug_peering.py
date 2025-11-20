#!/usr/bin/env python3
"""
Quick debug script to check if VPC Peering data is in collected_data.json
"""

import json
import sys

# Load the collected data
try:
    with open('collected_data.json', 'r') as f:
        data = json.load(f)
except FileNotFoundError:
    print("ERROR: collected_data.json not found")
    print("Please run: python3 aws_build_review-v2.3.2.py --output collected_data.json")
    sys.exit(1)

print("=== Checking VPC Peering Data ===\n")

# Check VPC structure
vpcs = data.get('VPC', {}).get('VPCs', [])
print(f"Found {len(vpcs)} VPC(s)\n")

for vpc in vpcs:
    vpc_id = vpc.get('VpcId', 'Unknown')
    print(f"VPC: {vpc_id}")
    
    # Check if VpcPeeringConnections key exists
    if 'VpcPeeringConnections' in vpc:
        peering = vpc.get('VpcPeeringConnections', [])
        print(f"  - VpcPeeringConnections key: EXISTS")
        print(f"  - Number of peering connections: {len(peering)}")
        
        if peering:
            for p in peering:
                peering_id = p.get('VpcPeeringConnectionId', 'Unknown')
                status = p.get('Status', {}).get('Code', 'Unknown')
                req_vpc = p.get('RequesterVpcInfo', {}).get('VpcId', 'Unknown')
                acc_vpc = p.get('AccepterVpcInfo', {}).get('VpcId', 'Unknown')
                print(f"    • {peering_id}: {req_vpc} <-> {acc_vpc} ({status})")
        else:
            print("    (No peering connections found)")
    else:
        print(f"  - VpcPeeringConnections key: MISSING")
        print(f"  - Available keys: {list(vpc.keys())}")
    
    print()

print("\n=== Checking verification_output.json ===\n")

try:
    with open('verification_output.json', 'r') as f:
        verify_data = json.load(f)
    
    # Check if CollectedData is preserved
    collected = verify_data.get('CollectedData', {})
    if collected:
        print("✓ CollectedData exists in verification_output.json")
        vpcs_in_verify = collected.get('VPC', {}).get('VPCs', [])
        print(f"✓ Found {len(vpcs_in_verify)} VPC(s) in CollectedData")
        
        for vpc in vpcs_in_verify:
            vpc_id = vpc.get('VpcId', 'Unknown')
            if 'VpcPeeringConnections' in vpc:
                peering_count = len(vpc.get('VpcPeeringConnections', []))
                print(f"  - {vpc_id}: {peering_count} peering connection(s)")
            else:
                print(f"  - {vpc_id}: VpcPeeringConnections key MISSING")
    else:
        print("✗ CollectedData is MISSING from verification_output.json")
        print("  This is the problem - verification script isn't preserving collected data!")
        
except FileNotFoundError:
    print("verification_output.json not found - run verification script first")
