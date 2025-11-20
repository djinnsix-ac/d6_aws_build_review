# Changelog

All notable changes to the AWS Build Review HTML Report Generator will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.2.0] - 2025-11-18

### Added
- **Tag-Based Risk Analysis**: Automatic risk assessment based on Environment and Data Classification tags
  - **Environment Tag Analysis**:
    - Development/Integration: Classified as non-production (lower risk)
    - Staging/Prep/Prod/Production: Classified as production with potential PII/PCI data (higher risk)
  - **Data Classification Tag Analysis**:
    - Internal: Low risk - available to organization members, no confidential data
    - Confidential: Medium-High risk - may contain PII, restricted to authorized personnel
    - Restricted: Critical risk - highest level PII (health/financial/religion/sexual orientation), PCI data, catastrophic damage potential
  - **Risk Level Calculation**: Combines environment and data classification to determine overall risk (CRITICAL/HIGH/MEDIUM/LOW)
  - **Visual Risk Indicators**: 
    - 🚨 emoji for CRITICAL risk buckets
    - ⚠️ emoji for HIGH risk buckets
    - Shown next to bucket name in main table
  - **Detailed Risk Analysis Panel**: Added to remediation section showing:
    - Overall risk level with color-coded badge
    - Environment classification (Production vs Non-Production)
    - Data classification level and description
    - Risk implications and warnings

### Changed
- Enhanced remediation section to include comprehensive risk context
- Risk analysis helps prioritize security remediation efforts based on data sensitivity and environment

## [2.1.3] - 2025-11-18

### Fixed
- **Tags Header Font Size**: Tags column header now matches all other headers in font size and weight (was incorrectly set to 11px)
- **Toggle Link Bug**: Fixed issue where clicking "Show less" would incorrectly change the "+6 more..." link text. Simplified toggle function to only control visibility without manipulating link text.

## [2.1.2] - 2025-11-18

### Fixed
- **Tag Display Duplication**: Fixed issue where clicking "more tags" would display ALL tags including the 3 already shown above the toggle link. Now correctly shows only additional tags (tags[3:]) when expanded
- **Table Layout for Tags**: Improved table spacing to provide more room for tag display:
  - Reduced font size in non-tag cells to 12px (from 14px)
  - Increased Tags column width to 25% of table
  - Reduced other column widths proportionally
  - Made badges and buttons more compact (10px and 11px fonts respectively)
  - Applied `.compact-cell` styling to all non-tag cells

### Changed
- Reorganized S3 table column widths:
  - Tags: 25% (increased for better visibility)
  - Bucket Name: 15%
  - Region: 8%
  - Versioning: 8%
  - Encryption: 8%
  - Public Block: 10%
  - Logging: 7%
  - Security Score: 9%
  - Action: 10%

## [2.1.1] - 2025-11-18

### Fixed
- **S3 Table Rendering**: Fixed critical issue where S3 buckets section would only show an empty table when buckets with issues existed
- **Empty State Logic**: Corrected condition that was incorrectly treating buckets with issues as "no issues" and showing the green checkmark instead of the table

### Technical Details
- Changed condition from `if not buckets_with_issues` to `if buckets_with_issues` to properly render the table
- Ensures table displays when `buckets_with_issues` list is populated
- Empty state (green checkmark) now only appears when list is actually empty

## [2.1.0] - 2025-11-17

### Added
- **Expandable Tag Display**: Added dynamic "more/less" toggle for S3 bucket tags
  - Shows first 3 tags by default
  - Displays "+N more..." link when >3 tags exist
  - Clicking expands to show all tags
  - "Show less" link collapses back to first 3
  - JavaScript-based, no page reload required

### Changed
- Improved S3 table tag cell formatting with better spacing
- Enhanced tag badge styling for better readability

## [2.0.0] - 2025-11-17

### Added
- **Enhanced S3 Bucket Tag Display**: 
  - Tags now display as colored badges with improved visibility
  - Automatic color coding: blue for standard tags, green for Environment, orange for Owner
  - Better visual hierarchy with consistent spacing
  - Maintains all tag information while improving readability

### Changed
- Refactored tag display from plain text list to badge-based system
- Updated CSS styling for tag badges with better contrast
- Improved table cell formatting for tags column

## [1.0.0] - 2025-11-15

### Added
- Initial release of HTML report generator
- Converts JSON verification reports to HTML format
- Summary cards showing issue counts by severity
- Detailed tables for S3 buckets and IAM roles
- Security scoring and risk indicators
- Responsive design with professional styling
- Command-line interface for easy execution

### Features
- **S3 Bucket Analysis**:
  - Versioning status
  - Encryption configuration
  - Public access block settings
  - Logging configuration
  - Tagging information
  - Security score calculation

- **IAM Role Analysis**:
  - Trust policy details
  - Attached policies
  - Last used information
  - Risk level indicators
  - Detailed descriptions

- **Visual Design**:
  - Color-coded severity levels
  - Status badges
  - Interactive tables
  - Professional typography
  - Responsive layout
