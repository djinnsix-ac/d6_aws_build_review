# Quick Start Guide - AWS Security Assessment Standalone App

## For Maintainers (You)

### Initial Setup (One Time Only)

```bash
# 1. Install Python 3.8+ if not already installed

# 2. Install build dependencies
pip install -r requirements_build.txt

# 3. You're ready to build!
```

### Building the Executable

**Windows:**
```batch
build_windows.bat
```

**Mac/Linux:**
```bash
chmod +x build_macos_linux.sh
./build_macos_linux.sh
```

**Output**: `dist/AWS-Security-Assessment.exe` (or equivalent)

**Time**: ~60-90 seconds

---

## Typical Workflow: Updating the Report Generator

**Scenario**: You've enhanced the HTML report (like we've been doing)

### Step 1: Update Your Script (Business as Usual)
```bash
# Edit and test your changes
vi generate_html_report-v2.13.11.py

# Save new version
cp generate_html_report-v2.13.11.py generate_html_report-v2.13.12.py

# Update version number inside the file (line 4)
# Version: 2.13.12

# Test it works
python generate_html_report-v2.13.12.py --input test.json --output test.html
```

### Step 2: Update the Wrapper (1 Minute)

Edit `aws_security_assessment_app.py`:

```python
# Line 33 - Change this:
REPORT_SCRIPT = "generate_html_report-v2.13.11.py"

# To this:
REPORT_SCRIPT = "generate_html_report-v2.13.12.py"
```

### Step 3: Update Build Script (1 Minute)

**If Windows** - Edit `build_windows.bat`:
```batch
REM Line 28 - Change this:
--add-data "generate_html_report-v2.13.11.py;." ^

REM To this:
--add-data "generate_html_report-v2.13.12.py;." ^
```

**If Mac/Linux** - Edit `build_macos_linux.sh`:
```bash
# Line 22 - Change this:
--add-data "generate_html_report-v2.13.11.py:." \

# To this:
--add-data "generate_html_report-v2.13.12.py:." \
```

### Step 4: Rebuild (1 Minute)
```bash
# Windows
build_windows.bat

# Mac/Linux
./build_macos_linux.sh
```

### Step 5: Test & Distribute
```bash
# Test the new executable
dist/AWS-Security-Assessment.exe

# If it works, distribute it!
# Just send users the .exe file - nothing else needed
```

**Total Time**: ~3-4 minutes from script update to new executable!

---

## Testing During Development

**Don't rebuild constantly!** Test the GUI directly:

```bash
# Run the wrapper without building
python aws_security_assessment_app.py

# This is much faster for testing:
# - UI changes
# - Credential handling
# - Workflow logic
# - Error messages
```

Only rebuild when you're ready to create a distributable executable.

---

## Common Update Scenarios

### Scenario A: Small Report Tweak (Most Common)
**Time**: 3 minutes
1. Update `generate_html_report-v2.13.X.py`
2. Update version in wrapper (1 line)
3. Update version in build script (1 line)
4. Run build script
5. Done!

### Scenario B: Collection Script Enhancement
**Time**: 3 minutes
1. Update `aws_build_review-v2.X.X.py`
2. Update `COLLECTION_SCRIPT` in wrapper
3. Update build script
4. Run build script
5. Done!

### Scenario C: GUI Enhancement (Rare)
**Time**: 5-10 minutes
1. Edit `aws_security_assessment_app.py`
2. Test with `python aws_security_assessment_app.py`
3. Iterate until satisfied
4. Run build script
5. Done!

### Scenario D: All Three Scripts Updated
**Time**: 4 minutes
1. Update all three version numbers in wrapper (3 lines)
2. Update all three in build script (3 lines)
3. Run build script
4. Done!

---

## File Organization

Recommended project structure:

```
aws-security-assessment-tool/
├── scripts/                          # Keep old versions here
│   ├── aws_build_review-v2.3.3.py
│   ├── aws_build_verification-v2.5.5.py
│   └── generate_html_report-v2.13.11.py
│
├── current/                          # Active versions (symlinks or copies)
│   ├── aws_build_review-v2.3.3.py
│   ├── aws_build_verification-v2.5.5.py
│   └── generate_html_report-v2.13.11.py
│
├── aws_security_assessment_app.py    # Wrapper application
├── build_windows.bat                 # Build script
├── build_macos_linux.sh             # Build script
├── requirements_build.txt           # Build dependencies
│
├── build/                           # PyInstaller temp (git ignore)
├── dist/                            # Output executables
│   └── AWS-Security-Assessment.exe
│
└── README_STANDALONE_APP.md         # Documentation
```

---

## Quick Reference

### Configuration Lines to Update

**In `aws_security_assessment_app.py`:**
```python
Lines 31-33:
COLLECTION_SCRIPT = "aws_build_review-vX.X.X.py"
VERIFICATION_SCRIPT = "aws_build_verification-vX.X.X.py"
REPORT_SCRIPT = "generate_html_report-vX.X.X.py"
```

**In `build_windows.bat`:**
```batch
Lines 26-28:
--add-data "aws_build_review-vX.X.X.py;." ^
--add-data "aws_build_verification-vX.X.X.py;." ^
--add-data "generate_html_report-vX.X.X.py;." ^
```

**In `build_macos_linux.sh`:**
```bash
Lines 20-22:
--add-data "aws_build_review-vX.X.X.py:." \
--add-data "aws_build_verification-vX.X.X.py:." \
--add-data "generate_html_report-vX.X.X.py:." \
```

---

## Tips for Efficiency

1. **Test scripts independently first** before updating wrapper
2. **Use search/replace** for version updates (don't type manually)
3. **Keep a build terminal open** for quick rebuilds
4. **Test on a VM** without Python to verify true standalone operation
5. **Version control everything** - git is your friend

---

## Troubleshooting

**Problem**: "Script not found" error when running executable

**Solution**: Check the `--add-data` paths in build script. Make sure the filename matches exactly.

---

**Problem**: Executable works on your machine but not on others

**Solution**: Test on a clean machine without Python installed. May need to add hidden imports.

---

**Problem**: Build takes forever

**Solution**: Delete `build/` and `dist/` folders first. PyInstaller caches can get corrupted.

---

**Problem**: Changes don't appear in new build

**Solution**: Use `--clean` flag or delete build folders manually.

---

That's it! The wrapper is designed to be low-maintenance. 95% of your work stays the same - just updating the core scripts!
