# AWS Security Assessment Tool - Standalone Application

**Version 1.0.0**  
**Copyright © 2025 Djinn Six Limited**

A self-contained desktop application that performs comprehensive AWS security assessments and generates detailed HTML reports. No installation required for end users!

---

## 🎯 For End Users

### What Is This?

A simple desktop application that:
1. Connects to your AWS account
2. Collects infrastructure data
3. Verifies against security best practices
4. Generates a comprehensive HTML report

### How to Use

1. **Download**: Get the executable file:
   - Windows: `AWS-Security-Assessment.exe`
   - Mac: `AWS-Security-Assessment.app`
   - Linux: `AWS-Security-Assessment` (binary)

2. **Run**: Double-click the file - that's it! No installation needed.

3. **Enter Credentials**: Choose one of:
   - Use an AWS profile (if you have AWS CLI configured)
   - Enter Access Key ID and Secret Access Key manually

4. **Configure**: Select your AWS region (e.g., `eu-west-1`)

5. **Run Assessment**: Click "Start Assessment" and wait 5-10 minutes

6. **View Report**: Click "Open HTML Report" when complete

### Requirements

- **Operating System**: Windows 10+, macOS 10.14+, or Linux
- **AWS Permissions**: Read-only access to AWS services (see below)
- **Internet**: Connection to AWS APIs
- **Nothing Else!** No Python, no AWS CLI, no dependencies

### AWS Permissions Required

The tool needs read-only access to AWS services. Recommended IAM policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:Describe*",
        "rds:Describe*",
        "s3:List*",
        "s3:GetBucket*",
        "lambda:List*",
        "lambda:Get*",
        "iam:List*",
        "iam:Get*",
        "cloudwatch:Describe*",
        "elasticache:Describe*",
        "ecs:Describe*",
        "ecs:List*",
        "eks:Describe*",
        "eks:List*",
        "opensearch:Describe*",
        "opensearch:List*",
        "sagemaker:Describe*",
        "sagemaker:List*",
        "bedrock:List*",
        "bedrock:Get*",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

### Security & Privacy

- ✅ Your credentials are **never stored** or sent anywhere except AWS
- ✅ All processing happens **locally on your computer**
- ✅ No data is transmitted to third parties
- ✅ Source code is available for review

---

## 🔧 For Developers / Maintainers

### Building the Executable

#### Prerequisites

```bash
# Install Python 3.8 or later
# Then install build dependencies:
pip install -r requirements_build.txt
```

#### Build Instructions

**Windows:**
```batch
build_windows.bat
```

**Mac/Linux:**
```bash
chmod +x build_macos_linux.sh
./build_macos_linux.sh
```

The executable will be created in the `dist/` folder.

### Project Structure

```
aws-security-assessment-tool/
├── aws_security_assessment_app.py       # Main GUI application
├── aws_build_review-v2.3.3.py          # Data collection script
├── aws_build_verification-v2.5.5.py    # Security verification script
├── generate_html_report-v2.13.11.py    # HTML report generator
├── build_windows.bat                    # Windows build script
├── build_macos_linux.sh                # Mac/Linux build script
├── requirements_build.txt              # Build dependencies
└── README.md                           # This file
```

### Updating the Scripts

When you update any of the three core scripts (collection, verification, or report generation):

1. **Save the new version** with updated version number:
   ```
   generate_html_report-v2.13.12.py  (example)
   ```

2. **Update the configuration** in `aws_security_assessment_app.py`:
   ```python
   # Line 31-33 (approximately)
   COLLECTION_SCRIPT = "aws_build_review-v2.3.3.py"
   VERIFICATION_SCRIPT = "aws_build_verification-v2.5.5.py"
   REPORT_SCRIPT = "generate_html_report-v2.13.12.py"  # ← Update this
   ```

3. **Update the build script** to include the new file:
   
   **Windows** (`build_windows.bat`):
   ```batch
   --add-data "generate_html_report-v2.13.12.py;." ^
   ```
   
   **Mac/Linux** (`build_macos_linux.sh`):
   ```bash
   --add-data "generate_html_report-v2.13.12.py:." \
   ```

4. **Rebuild the executable**:
   ```bash
   # Windows
   build_windows.bat
   
   # Mac/Linux
   ./build_macos_linux.sh
   ```

5. **Done!** Distribute the new executable from `dist/` folder.

**Time Required**: ~2-3 minutes total

### Testing Without Rebuilding

During development, you can run the GUI directly:

```bash
python aws_security_assessment_app.py
```

This is much faster for testing UI changes.

### Version Numbering

The wrapper app follows semantic versioning:
- **Major** (1.x.x): Breaking changes to GUI or workflow
- **Minor** (x.1.x): New features, significant improvements
- **Patch** (x.x.1): Bug fixes, minor tweaks

The three core scripts maintain their own version numbers independently.

### Adding New Features

#### To add a new configuration option:

1. Edit `create_configuration_tab()` in the app
2. Add the UI elements
3. Pass the new parameter to the scripts via command-line args

#### To add a new workflow step:

1. Edit `_run_assessment_thread()` in the app
2. Add your step between collection and report generation
3. Update progress messages

#### To change the UI layout:

1. Edit the relevant `create_*_tab()` method
2. Test with `python aws_security_assessment_app.py`
3. Rebuild when satisfied

### Build Size Optimization

The default build includes everything and is ~40-50MB. To reduce size:

1. **Use UPX compression** (Windows):
   ```batch
   pyinstaller ... --upx-dir C:\path\to\upx
   ```
   Can reduce to ~30MB

2. **Exclude unused modules**:
   ```python
   --exclude-module matplotlib --exclude-module PIL
   ```

3. **Use virtualenv** to avoid bundling unnecessary packages

### Troubleshooting Build Issues

**"Module not found" when running executable:**
- Make sure all imports are at module level (not inside functions)
- Add explicit hidden imports: `--hidden-import=module_name`

**Executable won't start:**
- Test with `--debug` flag: `pyinstaller --debug ...`
- Check `build/` folder for error logs

**Scripts not found at runtime:**
- Verify `--add-data` paths are correct
- Check `get_bundled_path()` function is working

**Antivirus blocks executable:**
- Sign the executable with a code signing certificate
- Submit to antivirus vendors for whitelisting

---

## 📋 Release Checklist

When releasing a new version:

- [ ] Update version number in `aws_security_assessment_app.py`
- [ ] Update `CHANGELOG.md` with changes
- [ ] Test on all target platforms (Windows, Mac, Linux)
- [ ] Build executables for all platforms
- [ ] Test each executable on clean machine (no Python installed)
- [ ] Create release notes
- [ ] Tag git repository: `git tag v1.0.0`
- [ ] Upload executables to distribution location
- [ ] Update documentation

---

## 🐛 Known Issues

None currently. Please report issues with:
- OS version
- AWS region
- Error message
- Log output

---

## 📄 License

Copyright © 2025 Djinn Six Limited  
All rights reserved.

This software is proprietary. Unauthorized copying, distribution, or modification is prohibited.

---

## 📞 Support

For support or questions:
- **Technical Issues**: Check logs in the application
- **Feature Requests**: Contact Djinn Six Limited
- **Security Concerns**: Email: [security contact]

---

## 🔄 Changelog

### Version 1.0.0 (2025-11-20)
- Initial release
- Self-contained executable for Windows, Mac, Linux
- Integrated collection, verification, and reporting
- Modern Tkinter GUI
- Support for AWS profiles and manual credentials
- Real-time progress logging
- One-click report viewing
- Export functionality

---

## 🚀 Future Enhancements

Planned features for future versions:
- [ ] Service-specific scan toggles
- [ ] Scheduled assessments
- [ ] Multi-region scanning
- [ ] Comparison with previous assessments
- [ ] Custom compliance frameworks
- [ ] Export to PDF/CSV
- [ ] Remediation suggestions
- [ ] Integration with ticketing systems

---

**Built with ❤️ by Djinn Six Limited**
