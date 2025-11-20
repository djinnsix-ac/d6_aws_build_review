# Debug Version - v2.9.2

## What's Wrong

The graph controls show but the graph area is blank. This means:
1. The HTML is loading correctly ✅
2. The data might be present but the JavaScript is failing ❌
3. OR the data array might be empty ❌

## New Debug Version

**generate_html_report-v2.9.2.py** adds console.log statements to diagnose the issue.

## How to Debug

### Step 1: Regenerate HTML with Debug Version
```bash
python3 generate_html_report-v2.9.2.py \
    --input your_verification.json \
    --output report_debug.html
```

### Step 2: Open Browser Console
1. Open `report_debug.html` in your browser
2. Press **F12** to open Developer Tools
3. Click **Console** tab
4. Expand the Security Groups section

### Step 3: Look for These Messages

**If data is present:**
```
Initializing security group graph
Security groups data: [Array of objects]
Number of security groups: 6
Graph dimensions: 1200 x 600
Created nodes: 6
Created links: 12
Sample node: {id: "sg-...", name: "...", ...}
Sample link: {source: "sg-...", target: "sg-...", ...}
Starting D3 visualization...
SVG created
```

**If data is missing:**
```
Initializing security group graph
Security groups data: []
Number of security groups: 0
ERROR: No security groups data available
```

**If JavaScript fails:**
You'll see red error messages like:
```
Uncaught ReferenceError: d3 is not defined
```
or
```
Uncaught TypeError: Cannot read property 'forEach' of undefined
```

### Step 4: What the Errors Mean

| Console Message | Problem | Solution |
|----------------|---------|----------|
| `Number of security groups: 0` | No data in JSON | Re-run verification with v2.5.1 |
| `d3 is not defined` | D3.js not loading | Check internet connection (CDN) |
| `Cannot read property 'forEach'` | Data format wrong | Check JSON structure |
| No messages at all | Function not called | Section not expanded or JS error |
| SVG created but blank | Nodes/links empty | Check sample node/link in console |

## Quick Checks

### Check 1: View Page Source
1. Right-click page → View Page Source
2. Search for: `securityGroupsData =`
3. Should see: `const securityGroupsData = [{...}, {...}, ...]`
4. NOT: `const securityGroupsData = []`

### Check 2: Verify JSON Structure
```bash
python3 check_sg_data_structure.py your_verification.json
```

Should show:
```
✅ Found nested 'SecurityGroups' array with X groups
✅ First security group has all required fields
```

### Check 3: Check File Sizes
```bash
ls -lh your_verification.json
```

If it's only a few KB, something went wrong with data collection.
Should be hundreds of KB or MB if it has real AWS data.

## What to Send Me

If it's still not working, send me:

1. **Console output** - Screenshot or copy/paste the console messages
2. **Verification JSON size** - Output of `ls -lh verification.json`
3. **Data structure check** - Output of `python3 check_sg_data_structure.py verification.json`

This will tell me exactly where the problem is.

## Current Versions

| Script | Version | Status |
|--------|---------|--------|
| aws_build_review | v2.3.0 | ✅ No change |
| aws_build_verification | v2.5.1 | ✅ No change |
| generate_html_report | v2.9.2 | ⚠️ **New debug version** |
