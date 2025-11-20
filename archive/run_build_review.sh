#!/bin/bash
# AWS Build Review Runner Script
# Convenience wrapper for running AWS infrastructure collection and verification

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
PROFILE=""
REGION=""
OUTPUT_DIR="./output"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Help function
show_help() {
    cat << EOF
AWS Build Review Runner

Usage: $0 [OPTIONS]

OPTIONS:
    -p, --profile PROFILE     AWS profile name (optional)
    -r, --region REGION       AWS region (optional)
    -o, --output DIR          Output directory (default: ./output)
    -s, --spec FILE           Design specification file for verification
    -m, --multi-region        Collect data from multiple regions
    -h, --help                Show this help message

EXAMPLES:
    # Basic collection with default credentials
    $0

    # Specify AWS profile and region
    $0 --profile prod-account --region eu-west-2

    # Include design specification verification
    $0 --profile staging --spec design_spec.json

    # Multi-region collection
    $0 --profile prod --multi-region

REGIONS FOR MULTI-REGION MODE:
    Edit the REGIONS array in this script to customize regions
EOF
}

# Parse command line arguments
MULTI_REGION=false
DESIGN_SPEC=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--profile)
            PROFILE="$2"
            shift 2
            ;;
        -r|--region)
            REGION="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -s|--spec)
            DESIGN_SPEC="$2"
            shift 2
            ;;
        -m|--multi-region)
            MULTI_REGION=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# Create output directory
mkdir -p "$OUTPUT_DIR"

echo -e "${GREEN}=== AWS Build Review Runner ===${NC}"
echo "Timestamp: $TIMESTAMP"
echo "Output Directory: $OUTPUT_DIR"
echo ""

# Function to collect data for a single region
collect_region() {
    local region=$1
    local output_file="${OUTPUT_DIR}/aws_review_${region}_${TIMESTAMP}.json"
    
    echo -e "${YELLOW}Collecting data for region: $region${NC}"
    
    # Build command
    cmd="python3 aws_build_review.py --output \"$output_file\""
    
    if [ -n "$PROFILE" ]; then
        cmd="$cmd --profile $PROFILE"
    fi
    
    if [ -n "$region" ]; then
        cmd="$cmd --region $region"
    fi
    
    # Execute collection
    eval $cmd
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Data collected: $output_file${NC}"
        
        # Run verification
        verify_report="${OUTPUT_DIR}/verification_${region}_${TIMESTAMP}.json"
        echo -e "${YELLOW}Running verification...${NC}"
        
        verify_cmd="python3 aws_build_verification.py --collected-data \"$output_file\" --output \"$verify_report\""
        
        if [ -n "$DESIGN_SPEC" ]; then
            verify_cmd="$verify_cmd --design-spec \"$DESIGN_SPEC\""
        fi
        
        eval $verify_cmd
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ Verification complete: $verify_report${NC}"
        else
            echo -e "${RED}✗ Verification failed${NC}"
        fi
    else
        echo -e "${RED}✗ Data collection failed for $region${NC}"
    fi
    
    echo ""
}

# Main execution
if [ "$MULTI_REGION" = true ]; then
    # Multi-region mode
    REGIONS=("eu-west-1" "eu-west-2" "us-east-1")
    
    echo -e "${YELLOW}Multi-region mode enabled${NC}"
    echo "Regions: ${REGIONS[*]}"
    echo ""
    
    for region in "${REGIONS[@]}"; do
        collect_region "$region"
    done
else
    # Single region mode
    collect_region "$REGION"
fi

# Generate summary
echo -e "${GREEN}=== Summary ===${NC}"
echo "Output files created in: $OUTPUT_DIR"
echo ""
echo "Files:"
ls -lh "$OUTPUT_DIR" | grep "$TIMESTAMP"
echo ""
echo -e "${GREEN}Build review complete!${NC}"

# Offer to generate combined report
if [ "$MULTI_REGION" = true ]; then
    echo ""
    echo -e "${YELLOW}Would you like to generate a combined report? (y/n)${NC}"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        combined_file="${OUTPUT_DIR}/combined_verification_${TIMESTAMP}.json"
        echo -e "${YELLOW}Generating combined report...${NC}"
        
        # Simple JSON array combination
        echo "[" > "$combined_file"
        first=true
        for file in "${OUTPUT_DIR}"/verification_*_${TIMESTAMP}.json; do
            if [ "$first" = true ]; then
                cat "$file" >> "$combined_file"
                first=false
            else
                echo "," >> "$combined_file"
                cat "$file" >> "$combined_file"
            fi
        done
        echo "]" >> "$combined_file"
        
        echo -e "${GREEN}✓ Combined report: $combined_file${NC}"
    fi
fi
