#!/bin/bash
# Build script for AWS Security Assessment Tool - Mac/Linux
# This creates a standalone binary that users can run without installing anything

echo "========================================"
echo "AWS Security Assessment Tool - Builder"
echo "========================================"
echo

# Check if PyInstaller is installed
if ! python3 -c "import PyInstaller" 2>/dev/null; then
    echo "PyInstaller not found. Installing..."
    pip3 install pyinstaller
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to install PyInstaller"
        exit 1
    fi
fi

echo
echo "Building standalone executable..."
echo "This may take 1-2 minutes..."
echo

# Build the executable
pyinstaller \
    --onefile \
    --windowed \
    --name "AWS-Security-Assessment" \
    --add-data "aws_build_review-v2.3.3.py:." \
    --add-data "aws_build_verification-v2.5.5.py:." \
    --add-data "generate_html_report-v2.13.11.py:." \
    --clean \
    aws_security_assessment_app.py

if [ $? -ne 0 ]; then
    echo
    echo "ERROR: Build failed!"
    exit 1
fi

echo
echo "========================================"
echo "BUILD SUCCESSFUL!"
echo "========================================"
echo
echo "Executable created: dist/AWS-Security-Assessment"
echo
echo "You can distribute this binary to users."
echo "Users just run it - no installation needed!"
echo

# Make executable on Mac/Linux
chmod +x dist/AWS-Security-Assessment

echo "Binary is now executable."
echo
