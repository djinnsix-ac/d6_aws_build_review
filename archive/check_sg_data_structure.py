#!/usr/bin/env python3
"""
Quick test to verify collected data structure for security group graph
Run this against your collected JSON to verify it has the right structure
"""

import json
import sys

def check_sg_data(json_file):
    """Check if collected data has the correct structure for SG graph"""
    
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    print("🔍 Checking data structure for security group network graph...\n")
    
    # Check top level
    if 'CollectedData' not in data:
        print("❌ FAIL: No 'CollectedData' key in JSON")
        return False
    
    collected = data['CollectedData']
    print("✅ Found 'CollectedData' key")
    
    # Check SecurityGroups level
    if 'SecurityGroups' not in collected:
        print("❌ FAIL: No 'SecurityGroups' key in CollectedData")
        return False
    
    sg_data = collected['SecurityGroups']
    print(f"✅ Found 'SecurityGroups' key: {type(sg_data)}")
    
    # Check nested SecurityGroups array
    if 'SecurityGroups' not in sg_data:
        print("❌ FAIL: No nested 'SecurityGroups' array")
        print(f"   Available keys: {list(sg_data.keys())}")
        return False
    
    sg_array = sg_data['SecurityGroups']
    print(f"✅ Found nested 'SecurityGroups' array with {len(sg_array)} groups")
    
    if len(sg_array) == 0:
        print("⚠️  WARNING: SecurityGroups array is empty")
        return False
    
    # Check first security group has required fields
    sg = sg_array[0]
    required_fields = ['GroupId', 'GroupName', 'IpPermissions', 'IpPermissionsEgress']
    missing = [f for f in required_fields if f not in sg]
    
    if missing:
        print(f"❌ FAIL: First security group missing fields: {missing}")
        print(f"   Available fields: {list(sg.keys())}")
        return False
    
    print(f"✅ First security group has all required fields")
    print(f"   GroupId: {sg['GroupId']}")
    print(f"   GroupName: {sg.get('GroupName', 'N/A')}")
    print(f"   Ingress rules: {len(sg.get('IpPermissions', []))}")
    print(f"   Egress rules: {len(sg.get('IpPermissionsEgress', []))}")
    
    # Check for interconnected rules (SG references)
    has_sg_refs = False
    for sg in sg_array:
        for rule in sg.get('IpPermissions', []):
            if rule.get('UserIdGroupPairs'):
                has_sg_refs = True
                break
        if has_sg_refs:
            break
    
    if has_sg_refs:
        print("✅ Found security group interconnections (good for graph)")
    else:
        print("⚠️  No SG-to-SG references found (graph will only show CIDR sources)")
    
    print(f"\n✅ SUCCESS: Data structure is correct for network graph!")
    print(f"   Total security groups: {len(sg_array)}")
    return True

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python3 check_sg_data_structure.py <verification_json_file>")
        sys.exit(1)
    
    try:
        success = check_sg_data(sys.argv[1])
        sys.exit(0 if success else 1)
    except FileNotFoundError:
        print(f"❌ ERROR: File not found: {sys.argv[1]}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ ERROR: Invalid JSON: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ ERROR: {e}")
        sys.exit(1)
