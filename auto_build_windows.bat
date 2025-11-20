@echo off
REM Automated Build Script for AWS Security Assessment Tool
REM This script checks for all required files and builds the executable automatically

echo ========================================
echo AWS Security Assessment - Auto Builder
echo ========================================
echo.

REM Check if we're in the right directory by looking for key files
if not exist "aws_security_assessment_app.py" (
    echo ERROR: aws_security_assessment_app.py not found!
    echo Please run this script from the directory containing all project files.
    pause
    exit /b 1
)

echo [1/5] Checking required files...
echo.

REM Required files list
set REQUIRED_FILES=aws_security_assessment_app.py requirements_build.txt

REM Check for assessment scripts (detect version automatically)
set FOUND_REVIEW=0
set FOUND_VERIFICATION=0
set FOUND_REPORT=0

for %%F in (aws_build_review-v*.py) do (
    set REVIEW_SCRIPT=%%F
    set FOUND_REVIEW=1
)

for %%F in (aws_build_verification-v*.py) do (
    set VERIFICATION_SCRIPT=%%F
    set FOUND_VERIFICATION=1
)

for %%F in (generate_html_report-v*.py) do (
    set REPORT_SCRIPT=%%F
    set FOUND_REPORT=1
)

REM Check all required files
set MISSING_FILES=0

for %%F in (%REQUIRED_FILES%) do (
    if not exist "%%F" (
        echo [ERROR] Missing: %%F
        set MISSING_FILES=1
    ) else (
        echo [OK] Found: %%F
    )
)

if %FOUND_REVIEW%==0 (
    echo [ERROR] Missing: aws_build_review-v*.py
    set MISSING_FILES=1
) else (
    echo [OK] Found: %REVIEW_SCRIPT%
)

if %FOUND_VERIFICATION%==0 (
    echo [ERROR] Missing: aws_build_verification-v*.py
    set MISSING_FILES=1
) else (
    echo [OK] Found: %VERIFICATION_SCRIPT%
)

if %FOUND_REPORT%==0 (
    echo [ERROR] Missing: generate_html_report-v*.py
    set MISSING_FILES=1
) else (
    echo [OK] Found: %REPORT_SCRIPT%
)

if %MISSING_FILES%==1 (
    echo.
    echo ERROR: Some required files are missing!
    echo Please ensure all files are in the same directory:
    echo   - aws_security_assessment_app.py
    echo   - aws_build_review-v*.py
    echo   - aws_build_verification-v*.py
    echo   - generate_html_report-v*.py
    echo   - requirements_build.txt
    pause
    exit /b 1
)

echo.
echo [2/5] Checking PyInstaller...

python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo PyInstaller not found. Installing build dependencies...
    pip install -r requirements_build.txt
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies
        pause
        exit /b 1
    )
)

echo [OK] PyInstaller is installed
echo.

echo [3/5] Cleaning previous build...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist
if exist "*.spec" del /q *.spec
echo [OK] Clean complete
echo.

echo [4/5] Building executable...
echo This may take 1-2 minutes...
echo.

REM Build the executable with auto-detected script versions
pyinstaller ^
    --onefile ^
    --windowed ^
    --name "AWS-Security-Assessment" ^
    --add-data "%REVIEW_SCRIPT%;." ^
    --add-data "%VERIFICATION_SCRIPT%;." ^
    --add-data "%REPORT_SCRIPT%;." ^
    --icon NONE ^
    --clean ^
    aws_security_assessment_app.py

if errorlevel 1 (
    echo.
    echo ERROR: Build failed!
    echo Check the output above for error messages.
    pause
    exit /b 1
)

echo.
echo [5/5] Verifying build...

if not exist "dist\AWS-Security-Assessment.exe" (
    echo ERROR: Executable was not created!
    pause
    exit /b 1
)

echo [OK] Build verification complete
echo.

REM Get file size
for %%F in (dist\AWS-Security-Assessment.exe) do set SIZE=%%~zF
set /a SIZE_MB=%SIZE% / 1048576

echo ========================================
echo BUILD SUCCESSFUL!
echo ========================================
echo.
echo Executable: dist\AWS-Security-Assessment.exe
echo Size: %SIZE_MB% MB
echo.
echo Scripts bundled:
echo   - %REVIEW_SCRIPT%
echo   - %VERIFICATION_SCRIPT%
echo   - %REPORT_SCRIPT%
echo.
echo You can now distribute dist\AWS-Security-Assessment.exe
echo Users just double-click it - no installation needed!
echo.
pause
