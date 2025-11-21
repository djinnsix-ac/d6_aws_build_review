#!/bin/bash
# Automated Build Script for AWS Security Assessment Tool
# This script checks for all required files and builds the executable automatically

echo "========================================"
echo "AWS Security Assessment - Auto Builder"
echo "========================================"
echo

# Check if we're in the right directory
if [ ! -f "aws_security_assessment_app.py" ]; then
    echo "ERROR: aws_security_assessment_app.py not found!"
    echo "Please run this script from the directory containing all project files."
    exit 1
fi

echo "[1/5] Checking required files..."
echo

# Required files
REQUIRED_FILES=(
    "aws_security_assessment_app.py"
    "requirements_build.txt"
)

# Auto-detect assessment script versions
REVIEW_SCRIPT=$(ls aws_build_review-v*.py 2>/dev/null | tail -n1)
VERIFICATION_SCRIPT=$(ls aws_build_verification-v*.py 2>/dev/null | tail -n1)
REPORT_SCRIPT=$(ls generate_html_report-v*.py 2>/dev/null | tail -n1)

MISSING_FILES=0

# Check required files
for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "[OK] Found: $file"
    else
        echo "[ERROR] Missing: $file"
        MISSING_FILES=1
    fi
done

# Check assessment scripts
if [ -z "$REVIEW_SCRIPT" ]; then
    echo "[ERROR] Missing: aws_build_review-v*.py"
    MISSING_FILES=1
else
    echo "[OK] Found: $REVIEW_SCRIPT"
fi

if [ -z "$VERIFICATION_SCRIPT" ]; then
    echo "[ERROR] Missing: aws_build_verification-v*.py"
    MISSING_FILES=1
else
    echo "[OK] Found: $VERIFICATION_SCRIPT"
fi

if [ -z "$REPORT_SCRIPT" ]; then
    echo "[ERROR] Missing: generate_html_report-v*.py"
    MISSING_FILES=1
else
    echo "[OK] Found: $REPORT_SCRIPT"
fi

if [ $MISSING_FILES -eq 1 ]; then
    echo
    echo "ERROR: Some required files are missing!"
    echo "Please ensure all files are in the same directory:"
    echo "  - aws_security_assessment_app.py"
    echo "  - aws_build_review-v*.py"
    echo "  - aws_build_verification-v*.py"
    echo "  - generate_html_report-v*.py"
    echo "  - requirements_build.txt"
    exit 1
fi

echo
echo "[2/5] Checking PyInstaller..."

if ! python3 -c "import PyInstaller" 2>/dev/null; then
    echo "PyInstaller not found. Installing build dependencies..."
    pip3 install -r requirements_build.txt
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to install dependencies"
        exit 1
    fi
fi

echo "[OK] PyInstaller is installed"
echo

echo "[3/5] Cleaning previous build..."
rm -rf build dist *.spec
echo "[OK] Clean complete"
echo

echo "[4/5] Building executable..."
echo "This may take 1-2 minutes..."
echo

# Build the executable with auto-detected script versions
pyinstaller \
    --onefile \
    --windowed \
    --name "AWS-Security-Assessment" \
    --add-data "$REVIEW_SCRIPT:." \
    --add-data "$VERIFICATION_SCRIPT:." \
    --add-data "$REPORT_SCRIPT:." \
    --clean \
    aws_security_assessment_app.py

if [ $? -ne 0 ]; then
    echo
    echo "ERROR: Build failed!"
    echo "Check the output above for error messages."
    exit 1
fi

echo
echo "[5/5] Verifying build..."

if [ ! -f "dist/AWS-Security-Assessment" ]; then
    echo "ERROR: Executable was not created!"
    exit 1
fi

# Make executable
chmod +x dist/AWS-Security-Assessment

echo "[OK] Build verification complete"
echo

# Get file size
SIZE=$(du -h dist/AWS-Security-Assessment | cut -f1)

echo "========================================"
echo "BUILD SUCCESSFUL!"
echo "========================================"
echo
echo "Executable: dist/AWS-Security-Assessment"
echo "Size: $SIZE"
echo
echo "Scripts bundled:"
echo "  - $REVIEW_SCRIPT"
echo "  - $VERIFICATION_SCRIPT"
echo "  - $REPORT_SCRIPT"
echo
echo "You can now distribute dist/AWS-Security-Assessment"
echo "Users just run it - no installation needed!"
echo
