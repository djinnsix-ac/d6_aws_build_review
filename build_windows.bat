@echo off
REM Build script for AWS Security Assessment Tool - Windows
REM This creates a standalone .exe file that users can run without installing anything

echo ========================================
echo AWS Security Assessment Tool - Builder
echo ========================================
echo.

REM Check if PyInstaller is installed
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo PyInstaller not found. Installing...
    pip install pyinstaller
    if errorlevel 1 (
        echo ERROR: Failed to install PyInstaller
        pause
        exit /b 1
    )
)

echo.
echo Building standalone executable...
echo This may take 1-2 minutes...
echo.

REM Build the executable
pyinstaller ^
    --onefile ^
    --windowed ^
    --name "AWS-Security-Assessment" ^
    --add-data "aws_build_review-v2.3.3.py;." ^
    --add-data "aws_build_verification-v2.5.5.py;." ^
    --add-data "generate_html_report-v2.13.11.py;." ^
    --icon NONE ^
    --clean ^
    aws_security_assessment_app.py

if errorlevel 1 (
    echo.
    echo ERROR: Build failed!
    pause
    exit /b 1
)

echo.
echo ========================================
echo BUILD SUCCESSFUL!
echo ========================================
echo.
echo Executable created: dist\AWS-Security-Assessment.exe
echo.
echo You can distribute this .exe file to users.
echo Users just double-click it - no installation needed!
echo.
pause
