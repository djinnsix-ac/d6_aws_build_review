# Project Setup - AWS Security Assessment Standalone App

## 📁 Directory Structure

All files MUST be in the same directory to build:

```
my-project-folder/
├── aws_security_assessment_app.py       # Main GUI app
├── aws_build_review-v2.3.3.py          # Collection script
├── aws_build_verification-v2.5.5.py    # Verification script
├── generate_html_report-v2.13.11.py    # Report generator
├── requirements_build.txt              # Build dependencies
├── auto_build_windows.bat              # Automated build (Windows)
└── auto_build_macos_linux.sh           # Automated build (Mac/Linux)
```

## 🚀 Quick Setup

### Step 1: Create Project Folder
```bash
mkdir aws-security-tool
cd aws-security-tool
```

### Step 2: Download All Files

Download and save all these files to your project folder:

**Required Files (7 total):**
1. aws_security_assessment_app.py
2. aws_build_review-v2.3.3.py
3. aws_build_verification-v2.5.5.py
4. generate_html_report-v2.13.11.py
5. requirements_build.txt
6. auto_build_windows.bat (if Windows)
7. auto_build_macos_linux.sh (if Mac/Linux)

### Step 3: Install Build Tools (One Time Only)

**Windows:**
```bash
pip install -r requirements_build.txt
```

**Mac/Linux:**
```bash
pip3 install -r requirements_build.txt
```

### Step 4: Build

**Windows:**
```bash
auto_build_windows.bat
```

**Mac/Linux:**
```bash
chmod +x auto_build_macos_linux.sh
./auto_build_macos_linux.sh
```

### Step 5: Test
```bash
# Windows
dist\AWS-Security-Assessment.exe

# Mac/Linux
dist/AWS-Security-Assessment
```

### Step 6: Distribute
Send users ONLY the executable file from the `dist/` folder!

---

## 🔄 When You Update Scripts

The automated build scripts detect versions automatically!

### Example: You update the report generator

1. **Save new version:**
   ```
   generate_html_report-v2.13.12.py
   ```

2. **Update the wrapper app:**
   Edit `aws_security_assessment_app.py` line 33:
   ```python
   REPORT_SCRIPT = "generate_html_report-v2.13.12.py"
   ```

3. **Rebuild:**
   ```bash
   auto_build_windows.bat
   ```

The automated script will:
- ✅ Check all files are present
- ✅ Detect the new version automatically
- ✅ Bundle it into the executable
- ✅ Report what was bundled

**That's it!** No need to edit build scripts - they auto-detect versions!

---

## 📦 What Gets Bundled

The executable includes:
- Python interpreter
- All libraries (boto3, tkinter, etc.)
- Your 3 assessment scripts (auto-detected versions)
- The GUI wrapper

Size: ~45 MB

---

## ✅ Automated Build Features

The new `auto_build` scripts:

✅ **Check for missing files** - Won't build if files are missing  
✅ **Auto-detect script versions** - No manual version editing in build script  
✅ **Install dependencies** - Installs PyInstaller if needed  
✅ **Clean builds** - Removes old build artifacts first  
✅ **Verify output** - Confirms executable was created  
✅ **Show bundled versions** - Tells you what was included  

---

## 🐛 Troubleshooting

**"File not found" error:**
- Make sure ALL 7 files are in the same directory
- Check file names match exactly (including version numbers)

**"PyInstaller not found":**
- Run: `pip install -r requirements_build.txt`

**Build script won't run (Mac/Linux):**
- Run: `chmod +x auto_build_macos_linux.sh`

**Executable won't start:**
- Test on clean machine without Python
- Check antivirus isn't blocking it

---

## 📝 File Checklist

Before building, verify you have:

- [ ] aws_security_assessment_app.py
- [ ] aws_build_review-v2.3.3.py (or later version)
- [ ] aws_build_verification-v2.5.5.py (or later version)
- [ ] generate_html_report-v2.13.11.py (or later version)
- [ ] requirements_build.txt
- [ ] auto_build_windows.bat OR auto_build_macos_linux.sh

All files in the **same directory**!

---

## 🎯 Key Points

1. **All files must be in same directory** ✅
2. **Automated build detects versions automatically** ✅
3. **Only 1 line to change when updating scripts** ✅
4. **Build time: ~60 seconds** ✅
5. **Distribute: Just the .exe file** ✅

---

## 💡 Pro Tip

Keep your project organized:

```
aws-security-tool/
├── source/                    # All source files here
│   ├── aws_security_assessment_app.py
│   ├── aws_build_review-v2.3.3.py
│   ├── aws_build_verification-v2.5.5.py
│   ├── generate_html_report-v2.13.11.py
│   ├── requirements_build.txt
│   └── auto_build_windows.bat
│
├── dist/                      # Built executables
│   └── AWS-Security-Assessment.exe
│
└── releases/                  # Archived releases
    ├── v1.0.0/
    └── v1.0.1/
```

Run build script from the `source/` directory.

---

**Ready to build!** 🚀
