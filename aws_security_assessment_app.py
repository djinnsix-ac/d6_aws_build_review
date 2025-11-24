#!/usr/bin/env python3
"""
AWS Security Assessment Tool - Standalone GUI Application
Version: 1.0.2
Date: 2025-11-20

Changelog:
- v1.0.2: Fix verification script argument mismatch and report opening
  - Changed --input to --collected-data for verification script (line 487)
  - Removed new=2 parameter from webbrowser.open to prevent new window spawning
- v1.0.1: Fix bugs with subprocess launching new app instances
  - Test Connection now uses boto3 directly instead of subprocess
  - Assessment execution uses system Python instead of sys.executable
- v1.0.0: Initial release

A self-contained application that collects AWS infrastructure data,
performs security verification, and generates comprehensive HTML reports.

NO INSTALLATION REQUIRED - Just run the executable!

Copyright (c) 2025 Djinn Six Limited
"""

import sys
import os
import json
import subprocess
import threading
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import tempfile

# ============================================================================
# CONFIGURATION - UPDATE THESE WHEN YOU CHANGE SCRIPT VERSIONS
# ============================================================================
COLLECTION_SCRIPT = "aws_build_review-v2.4.1.py"
VERIFICATION_SCRIPT = "aws_build_verification-v2.7.1.py"
REPORT_SCRIPT = "generate_html_report-v2.16.0.py"

APP_VERSION = "1.0.2"
APP_NAME = "AWS Security Assessment Tool"

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_bundled_path(filename):
    """Get path to bundled resource file (works with PyInstaller)"""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        bundle_dir = sys._MEIPASS
    else:
        # Running as script
        bundle_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(bundle_dir, filename)


def get_aws_profiles():
    """Read AWS profiles from ~/.aws/credentials"""
    profiles = []
    credentials_path = Path.home() / '.aws' / 'credentials'
    
    if credentials_path.exists():
        try:
            with open(credentials_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('[') and line.endswith(']'):
                        profile = line[1:-1]
                        profiles.append(profile)
        except Exception as e:
            print(f"Could not read AWS profiles: {e}")
    
    return profiles


def get_aws_regions():
    """Return list of common AWS regions"""
    return [
        'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
        'eu-west-1', 'eu-west-2', 'eu-west-3', 'eu-central-1', 'eu-north-1',
        'ap-south-1', 'ap-northeast-1', 'ap-northeast-2', 'ap-southeast-1', 'ap-southeast-2',
        'ca-central-1', 'sa-east-1',
        'af-south-1', 'ap-east-1', 'me-south-1'
    ]


# ============================================================================
# MAIN APPLICATION CLASS
# ============================================================================

class AWSSecurityAssessmentApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.geometry("900x700")
        
        # Variables
        self.use_profile = tk.BooleanVar(value=True)
        self.profile_name = tk.StringVar()
        self.access_key = tk.StringVar()
        self.secret_key = tk.StringVar()
        self.session_token = tk.StringVar()
        self.region = tk.StringVar(value='eu-west-1')
        
        self.is_running = False
        self.output_dir = None
        self.report_path = None
        
        # Build UI
        self.create_ui()
        
        # Load AWS profiles
        profiles = get_aws_profiles()
        if profiles:
            self.profile_combo['values'] = profiles
            self.profile_name.set(profiles[0] if profiles else 'default')
        else:
            self.use_profile.set(False)
            self.toggle_credential_mode()
    
    def create_ui(self):
        """Create the user interface"""
        
        # Create notebook (tabs)
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Tab 1: Credentials
        cred_frame = ttk.Frame(notebook)
        notebook.add(cred_frame, text="1. Credentials")
        self.create_credentials_tab(cred_frame)
        
        # Tab 2: Configuration
        config_frame = ttk.Frame(notebook)
        notebook.add(config_frame, text="2. Configuration")
        self.create_configuration_tab(config_frame)
        
        # Tab 3: Run Assessment
        run_frame = ttk.Frame(notebook)
        notebook.add(run_frame, text="3. Run Assessment")
        self.create_run_tab(run_frame)
        
        # Status bar at bottom
        self.status_bar = ttk.Label(self.root, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def create_credentials_tab(self, parent):
        """Create credentials input tab"""
        
        # Title
        title = ttk.Label(parent, text="AWS Credentials", font=('Arial', 14, 'bold'))
        title.pack(pady=10)
        
        # Profile mode radio
        profile_radio = ttk.Radiobutton(
            parent, 
            text="Use AWS Profile (from ~/.aws/credentials)", 
            variable=self.use_profile, 
            value=True,
            command=self.toggle_credential_mode
        )
        profile_radio.pack(anchor=tk.W, padx=20, pady=5)
        
        # Profile selection frame
        self.profile_frame = ttk.Frame(parent)
        self.profile_frame.pack(fill=tk.X, padx=40, pady=5)
        
        ttk.Label(self.profile_frame, text="Profile Name:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.profile_combo = ttk.Combobox(self.profile_frame, textvariable=self.profile_name, width=30)
        self.profile_combo.grid(row=0, column=1, sticky=tk.W, pady=5, padx=10)
        
        # Manual mode radio
        manual_radio = ttk.Radiobutton(
            parent, 
            text="Enter Credentials Manually", 
            variable=self.use_profile, 
            value=False,
            command=self.toggle_credential_mode
        )
        manual_radio.pack(anchor=tk.W, padx=20, pady=(20, 5))
        
        # Manual credential frame
        self.manual_frame = ttk.Frame(parent)
        self.manual_frame.pack(fill=tk.X, padx=40, pady=5)
        
        ttk.Label(self.manual_frame, text="Access Key ID:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.access_key_entry = ttk.Entry(self.manual_frame, textvariable=self.access_key, width=40)
        self.access_key_entry.grid(row=0, column=1, sticky=tk.W, pady=5, padx=10)
        
        ttk.Label(self.manual_frame, text="Secret Access Key:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.secret_key_entry = ttk.Entry(self.manual_frame, textvariable=self.secret_key, width=40, show="*")
        self.secret_key_entry.grid(row=1, column=1, sticky=tk.W, pady=5, padx=10)
        
        ttk.Label(self.manual_frame, text="Session Token (optional):").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.session_token_entry = ttk.Entry(self.manual_frame, textvariable=self.session_token, width=40)
        self.session_token_entry.grid(row=2, column=1, sticky=tk.W, pady=5, padx=10)
        
        # Test connection button
        test_btn = ttk.Button(parent, text="Test Connection", command=self.test_connection)
        test_btn.pack(pady=20)
        
        # Info text
        info_text = ttk.Label(
            parent, 
            text="Note: Credentials are used only for this session and are not stored.",
            font=('Arial', 9, 'italic'),
            foreground='gray'
        )
        info_text.pack(pady=10)
        
        # Initialize state
        self.toggle_credential_mode()
    
    def create_configuration_tab(self, parent):
        """Create configuration tab"""
        
        # Title
        title = ttk.Label(parent, text="Assessment Configuration", font=('Arial', 14, 'bold'))
        title.pack(pady=10)
        
        # Region selection
        region_frame = ttk.LabelFrame(parent, text="AWS Region", padding=10)
        region_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Label(region_frame, text="Region:").pack(side=tk.LEFT, padx=5)
        region_combo = ttk.Combobox(region_frame, textvariable=self.region, values=get_aws_regions(), width=20)
        region_combo.pack(side=tk.LEFT, padx=5)
        
        # Services to scan (for future enhancement)
        services_frame = ttk.LabelFrame(parent, text="Services to Scan", padding=10)
        services_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        info = ttk.Label(
            services_frame,
            text="Currently scans all available services:\n\n"
                 "• VPC Architecture\n"
                 "• Security Groups\n"
                 "• Compute (EC2, Lambda, ECS, EKS)\n"
                 "• Load Balancers\n"
                 "• Databases (RDS, ElastiCache, OpenSearch)\n"
                 "• Storage (S3)\n"
                 "• IAM\n"
                 "• Monitoring (CloudWatch)\n"
                 "• SageMaker & Bedrock\n"
                 "• CIS Benchmarks",
            justify=tk.LEFT
        )
        info.pack(anchor=tk.W)
    
    def create_run_tab(self, parent):
        """Create run assessment tab"""
        
        # Title
        title = ttk.Label(parent, text="Run Security Assessment", font=('Arial', 14, 'bold'))
        title.pack(pady=10)
        
        # Output directory selection
        output_frame = ttk.Frame(parent)
        output_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Label(output_frame, text="Output Directory:").pack(side=tk.LEFT, padx=5)
        self.output_dir_label = ttk.Label(output_frame, text="(Will use temporary directory)", foreground='gray')
        self.output_dir_label.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(output_frame, text="Choose...", command=self.choose_output_dir).pack(side=tk.LEFT, padx=5)
        
        # Run button
        self.run_btn = ttk.Button(
            parent, 
            text="▶ Start Assessment", 
            command=self.run_assessment,
            style='Accent.TButton'
        )
        self.run_btn.pack(pady=20)
        
        # Progress bar
        self.progress = ttk.Progressbar(parent, mode='indeterminate')
        self.progress.pack(fill=tk.X, padx=20, pady=5)
        
        # Status label
        self.status_label = ttk.Label(parent, text="", font=('Arial', 10))
        self.status_label.pack(pady=5)
        
        # Log output
        log_frame = ttk.LabelFrame(parent, text="Progress Log", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Results buttons frame
        self.results_frame = ttk.Frame(parent)
        self.results_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.open_report_btn = ttk.Button(
            self.results_frame, 
            text="📄 Open HTML Report", 
            command=self.open_report,
            state=tk.DISABLED
        )
        self.open_report_btn.pack(side=tk.LEFT, padx=5)
        
        self.save_files_btn = ttk.Button(
            self.results_frame, 
            text="💾 Save All Files", 
            command=self.save_all_files,
            state=tk.DISABLED
        )
        self.save_files_btn.pack(side=tk.LEFT, padx=5)
    
    def toggle_credential_mode(self):
        """Enable/disable credential input fields based on mode"""
        if self.use_profile.get():
            # Enable profile, disable manual
            for child in self.profile_frame.winfo_children():
                child.configure(state=tk.NORMAL)
            for child in self.manual_frame.winfo_children():
                if isinstance(child, (ttk.Entry, ttk.Combobox)):
                    child.configure(state=tk.DISABLED)
        else:
            # Disable profile, enable manual
            for child in self.profile_frame.winfo_children():
                if isinstance(child, (ttk.Entry, ttk.Combobox)):
                    child.configure(state=tk.DISABLED)
            for child in self.manual_frame.winfo_children():
                child.configure(state=tk.NORMAL)
    
    def test_connection(self):
        """Test AWS connection with provided credentials"""
        self.log_message("Testing AWS connection...")
        
        # Import boto3 directly instead of subprocess
        import boto3
        
        try:
            # Set up credentials
            if self.use_profile.get():
                os.environ['AWS_PROFILE'] = self.profile_name.get()
                cred_info = f"profile '{self.profile_name.get()}'"
            else:
                if not self.access_key.get() or not self.secret_key.get():
                    messagebox.showerror("Error", "Please enter Access Key ID and Secret Access Key")
                    return
                os.environ['AWS_ACCESS_KEY_ID'] = self.access_key.get()
                os.environ['AWS_SECRET_ACCESS_KEY'] = self.secret_key.get()
                if self.session_token.get():
                    os.environ['AWS_SESSION_TOKEN'] = self.session_token.get()
                cred_info = "provided credentials"
            
            os.environ['AWS_DEFAULT_REGION'] = self.region.get()
            
            # Test connection directly with boto3
            sts = boto3.client('sts', region_name=self.region.get())
            identity = sts.get_caller_identity()
            
            account = identity['Account']
            arn = identity['Arn']
            
            self.log_message(f"✅ Connection successful!")
            self.log_message(f"   Account: {account}")
            self.log_message(f"   Identity: {arn}")
            messagebox.showinfo(
                "Success", 
                f"AWS connection successful!\n\nAccount: {account}\nRegion: {self.region.get()}"
            )
        
        except Exception as e:
            self.log_message(f"❌ Connection failed: {str(e)}")
            messagebox.showerror("Connection Failed", f"Could not connect to AWS:\n\n{str(e)}")
    
    def choose_output_dir(self):
        """Let user choose output directory"""
        directory = filedialog.askdirectory(title="Choose Output Directory")
        if directory:
            self.output_dir = directory
            self.output_dir_label.config(text=directory, foreground='black')
    
    def log_message(self, message):
        """Add message to log output"""
        self.log_text.configure(state=tk.NORMAL)
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)
        self.root.update_idletasks()
    
    def update_status(self, message):
        """Update status label and status bar"""
        self.status_label.config(text=message)
        self.status_bar.config(text=message)
        self.root.update_idletasks()
    
    def run_assessment(self):
        """Run the full AWS security assessment"""
        if self.is_running:
            messagebox.showwarning("Already Running", "Assessment is already in progress!")
            return
        
        # Validate credentials
        if not self.use_profile.get():
            if not self.access_key.get() or not self.secret_key.get():
                messagebox.showerror("Error", "Please enter AWS credentials or select a profile")
                return
        
        # Confirm
        if not messagebox.askyesno(
            "Confirm Assessment",
            f"Ready to run security assessment on AWS account in {self.region.get()} region.\n\n"
            "This will:\n"
            "1. Collect infrastructure data\n"
            "2. Verify against security standards\n"
            "3. Generate HTML report\n\n"
            "This may take 5-10 minutes depending on your infrastructure size.\n\n"
            "Continue?"
        ):
            return
        
        # Run in background thread
        thread = threading.Thread(target=self._run_assessment_thread, daemon=True)
        thread.start()
    
    def _run_assessment_thread(self):
        """Background thread to run assessment"""
        self.is_running = True
        
        # UI updates
        self.run_btn.configure(state=tk.DISABLED)
        self.progress.start()
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state=tk.DISABLED)
        
        try:
            # Create output directory
            if not self.output_dir:
                self.output_dir = tempfile.mkdtemp(prefix='aws_assessment_')
                self.log_message(f"Using temporary directory: {self.output_dir}")
            else:
                self.log_message(f"Output directory: {self.output_dir}")
            
            # Setup environment
            env = os.environ.copy()
            if self.use_profile.get():
                env['AWS_PROFILE'] = self.profile_name.get()
            else:
                env['AWS_ACCESS_KEY_ID'] = self.access_key.get()
                env['AWS_SECRET_ACCESS_KEY'] = self.secret_key.get()
                if self.session_token.get():
                    env['AWS_SESSION_TOKEN'] = self.session_token.get()
            env['AWS_DEFAULT_REGION'] = self.region.get()
            
            # File paths
            collected_json = os.path.join(self.output_dir, 'collected_data.json')
            verification_json = os.path.join(self.output_dir, 'verification_results.json')
            report_html = os.path.join(self.output_dir, 'security_assessment_report.html')
            
            # Step 1: Data Collection
            self.update_status("Step 1/3: Collecting AWS infrastructure data...")
            self.log_message("=" * 60)
            self.log_message("STEP 1: Collecting AWS Infrastructure Data")
            self.log_message("=" * 60)
            
            collection_script = get_bundled_path(COLLECTION_SCRIPT)
            result = self._run_script(
                collection_script,
                ['--region', self.region.get(), '--output', collected_json],
                env
            )
            
            if result != 0:
                self.log_message("❌ Data collection failed!")
                messagebox.showerror("Error", "Data collection failed. Check the log for details.")
                return
            
            self.log_message("✅ Data collection completed successfully")
            
            # Step 2: Verification
            self.update_status("Step 2/3: Verifying against security standards...")
            self.log_message("")
            self.log_message("=" * 60)
            self.log_message("STEP 2: Verifying Against Security Standards")
            self.log_message("=" * 60)
            
            verification_script = get_bundled_path(VERIFICATION_SCRIPT)
            result = self._run_script(
                verification_script,
                ['--collected-data', collected_json, '--output', verification_json],
                env
            )
            
            if result != 0:
                self.log_message("❌ Verification failed!")
                messagebox.showerror("Error", "Verification failed. Check the log for details.")
                return
            
            self.log_message("✅ Verification completed successfully")
            
            # Step 3: Report Generation
            self.update_status("Step 3/3: Generating HTML report...")
            self.log_message("")
            self.log_message("=" * 60)
            self.log_message("STEP 3: Generating HTML Report")
            self.log_message("=" * 60)
            
            report_script = get_bundled_path(REPORT_SCRIPT)
            result = self._run_script(
                report_script,
                ['--input', verification_json, '--output', report_html],
                env
            )
            
            if result != 0:
                self.log_message("❌ Report generation failed!")
                messagebox.showerror("Error", "Report generation failed. Check the log for details.")
                return
            
            self.log_message("✅ Report generated successfully")
            
            # Success!
            self.report_path = report_html
            self.log_message("")
            self.log_message("=" * 60)
            self.log_message("✅ ASSESSMENT COMPLETE!")
            self.log_message("=" * 60)
            self.log_message(f"Report: {report_html}")
            self.log_message(f"Data: {collected_json}")
            self.log_message(f"Verification: {verification_json}")
            
            self.update_status("Assessment completed successfully!")
            
            # Enable result buttons
            self.open_report_btn.configure(state=tk.NORMAL)
            self.save_files_btn.configure(state=tk.NORMAL)
            
            # Show success dialog
            self.root.after(0, lambda: messagebox.showinfo(
                "Success",
                "AWS Security Assessment completed successfully!\n\n"
                f"Report saved to:\n{report_html}\n\n"
                "Click 'Open HTML Report' to view it."
            ))
            
        except Exception as e:
            self.log_message(f"❌ Error: {e}")
            import traceback
            self.log_message(traceback.format_exc())
            self.root.after(0, lambda: messagebox.showerror("Error", f"Assessment failed:\n\n{e}"))
        
        finally:
            self.is_running = False
            self.run_btn.configure(state=tk.NORMAL)
            self.progress.stop()
            self.update_status("Ready")
    
    def _run_script(self, script_path, args, env):
        """Run a Python script and capture output
        
        When bundled, we can't use subprocess with sys.executable as it points to the app.
        Instead, we'll import and run the script directly.
        """
        try:
            # For now, use subprocess with 'python3' command
            # This assumes Python 3 is installed on the system
            import shutil
            
            # Try to find python3 or python
            python_cmd = shutil.which('python3') or shutil.which('python')
            
            if not python_cmd:
                raise Exception("Python not found in system PATH. Please install Python 3.")
            
            cmd = [python_cmd, script_path] + args
            
            self.log_message(f"Running: {os.path.basename(script_path)}...")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,
                bufsize=1
            )
            
            # Stream output
            for line in process.stdout:
                self.log_message(line.rstrip())
            
            process.wait()
            return process.returncode
            
        except Exception as e:
            self.log_message(f"Error running script: {e}")
            import traceback
            self.log_message(traceback.format_exc())
            return 1
    
    def open_report(self):
        """Open the HTML report in default browser"""
        if self.report_path and os.path.exists(self.report_path):
            import webbrowser
            webbrowser.open(f'file://{os.path.abspath(self.report_path)}')
            self.log_message(f"Opened report in browser: {self.report_path}")
        else:
            messagebox.showerror("Error", "Report file not found!")
    
    def save_all_files(self):
        """Save all output files to user-chosen directory"""
        if not self.output_dir:
            messagebox.showerror("Error", "No files to save!")
            return
        
        dest_dir = filedialog.askdirectory(title="Choose Destination Directory")
        if dest_dir:
            try:
                import shutil
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_folder = os.path.join(dest_dir, f"aws_assessment_{timestamp}")
                
                shutil.copytree(self.output_dir, output_folder)
                
                self.log_message(f"✅ All files saved to: {output_folder}")
                messagebox.showinfo("Success", f"All files saved to:\n\n{output_folder}")
                
                # Open folder
                if sys.platform == 'win32':
                    os.startfile(output_folder)
                elif sys.platform == 'darwin':
                    subprocess.run(['open', output_folder])
                else:
                    subprocess.run(['xdg-open', output_folder])
                    
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save files:\n\n{e}")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Main entry point"""
    root = tk.Tk()
    
    # Set icon if available
    try:
        if sys.platform == 'win32':
            root.iconbitmap(get_bundled_path('icon.ico'))
    except:
        pass
    
    # Configure ttk style
    style = ttk.Style()
    style.theme_use('clam')
    
    # Create and run app
    app = AWSSecurityAssessmentApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
