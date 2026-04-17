# PythonAnywhere Flask Deployment Guide - 2026 Edition

## ⚠️ IMPORTANT: Use Manual Configuration (Not Quickstart)

For existing projects, choose **"Manual Configuration"** when creating your web app.

---

## Step 1: Clean Setup (Fresh Start)

```bash
# Remove everything and start fresh
cd /home/daimondp
rm -rf buzzbuuzz/
git clone https://github.com/Wollyonix/Buzzbuuzz.git buzzbuuzz
cd buzzbuuzz
```

---

## Step 2: Create Virtual Environment

```bash
# Check your system image first (Account → System Image)
# For innit system image (most common in 2026):
mkvirtualenv -p /usr/local/bin/python3.11 buzzbuuzz-env

# For older systems:
# mkvirtualenv --python=/usr/bin/python3.11 buzzbuuzz-env

# Activate
workon buzzbuuzz-env
```

---

## Step 3: Install Dependencies

```bash
pip install -r requirements.txt
pip install python-dotenv  # For environment variables
```

---

## Step 4: Create .env File for Environment Variables

```bash
# Create .env file in your project root
echo "SESSION_SECRET=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2" > .env
```

---

## Step 5: Update WSGI File

Your `wsgi.py` should be:

```python
import os
import sys
from dotenv import load_dotenv

# Add project to path
project_home = '/home/daimondp/buzzbuuzz'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Load environment variables FIRST
load_dotenv(os.path.join(project_home, '.env'))

# Import Flask app
from app import app as application
```

---

## Step 6: Web App Configuration

1. **Web** tab → **Add a new web app**
2. Choose **Manual Configuration** (not quickstart)
3. **Domain:** `daimondp.pythonanywhere.com`
4. **Python version:** `3.11`
5. **Virtualenv:** `buzzbuuzz-env` (type it, system will auto-complete path)

---

## Step 7: Configure Paths

In the web app settings:
- **Source code:** `/home/daimondp/buzzbuuzz`
- **Working directory:** `/home/daimondp/buzzbuuzz`
- **WSGI file:** `/home/daimondp/buzzbuuzz/wsgi.py`
- **Static files:** URL=`/static/` Directory=`/home/daimondp/buzzbuuzz/static`

---

## Step 8: Reload & Test

1. Click **"Reload"** button
2. Wait 2-3 minutes
3. Visit: `https://daimondp.pythonanywhere.com`

---

## 🔍 Troubleshooting

**502 Error:**
- Check WSGI file syntax
- Verify virtualenv is activated
- Check error logs in Web tab

**Import Errors:**
- Make sure python-dotenv is installed
- Verify .env file exists and is readable

**Environment Variable Issues:**
- .env file must be loaded BEFORE app import in WSGI
- Check file permissions: `chmod 600 .env`

---

## 📞 Current PythonAnywhere Features (2026)

- **System Images:** innit (latest), classic
- **Python:** 3.8 - 3.13 available
- **AI Tools:** Claude, Copilot integration
- **Environment Variables:** python-dotenv method recommended

---

## Step 2: Create Virtual Environment

```bash
python3.11 -m venv venv
source venv/bin/activate
```

---

## Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Step 4: Create WSGI Configuration

Create `wsgi.py` in your project root with this exact content:

```python
import os
import sys

project_home = '/home/daimondp/buzzbuuzz'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

activate_this = os.path.expanduser('/home/daimondp/buzzbuuzz/venv/bin/activate_this.py')
exec(open(activate_this).read())

from app import app as application
```

**✅ I've already created this file for you - it's ready to use!**

---

## Step 5: Configure Web App

1. Go to **"Web"** tab → **"Add a new web app"**
2. Choose:
   - Domain: `daimondp.pythonanywhere.com`
   - Framework: **Flask**
   - Python: **3.11**

3. **WSGI file**: Point to `/home/daimondp/buzzbuuzz/wsgi.py`

---

## Step 6: Set Environment Variable

1. In **"Web"** tab → **"Environment variables"**
2. Add:
   - Name: `SESSION_SECRET`
   - Value: Generate with `python3 -c "import secrets; print(secrets.token_hex(32))"`

---

## Step 7: Reload & Test

1. Click **"Reload"** button
2. Visit `https://YOUR_USERNAME.pythonanywhere.com`

---

## If You Don't Have a Repo Yet

Upload files manually:
1. **"Files"** tab → Create `buzzbuuzz` folder
2. Upload all project files
3. Continue from Step 2 above

---

## Quick Commands Summary

```bash
# Clone repo
cd /home/daimondp
git clone https://github.com/Wollyonix/Buzzbuuzz.git buzzbuuzz
cd buzzbuuzz

# Setup environment
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create wsgi.py (already done for you)
# Then configure web app in dashboard
```

---

## Troubleshooting

- **502 Error**: Check WSGI file path and YOUR_USERNAME replacement
- **Session Secret Error**: Environment variable not set
- **Import Errors**: Virtual environment not activated in WSGI

---

## Step 2: Create Virtual Environment

1. Go to **"Consoles"** → Click **"Bash"**
2. Run:
```bash
cd /home/YOUR_USERNAME/buzzbuuzz
python3.11 -m venv venv
source venv/bin/activate
```

3. Verify it's activated (you should see `(venv)` at the prompt)

---

## Step 3: Install Dependencies

With the virtual environment activated, run:

```bash
pip install -r requirements.txt
```

Wait for installation to complete. You should see:
```
Successfully installed flask flask-cors requests gunicorn ...
```

---

## Step 4: Create WSGI Configuration File

The WSGI file is what PythonAnywhere uses to run your Flask app.

1. In your `buzzbuuzz` folder, create a file named `wsgi.py`:

```python
# /home/YOUR_USERNAME/buzzbuuzz/wsgi.py
import os
import sys

# Add the project directory to the path
project_home = '/home/YOUR_USERNAME/buzzbuuzz'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Activate virtual environment
activate_this = os.path.expanduser('/home/YOUR_USERNAME/buzzbuuzz/venv/bin/activate_this.py')
exec(open(activate_this).read())

# Import and configure the Flask app
from app import app as application
```

⚠️ **IMPORTANT**: Replace `YOUR_USERNAME` with your actual PythonAnywhere username (2 times)

---

## Step 5: Configure Web App in PythonAnywhere

1. Go to **"Web"** tab → Click **"Add a new web app"**
2. Choose:
   - **Domain**: `YOUR_USERNAME.pythonanywhere.com` (free option)
   - **Python web framework**: Select **"Flask"**
   - **Python version**: Select **3.11** (or latest available)

3. **WSGI Configuration File**: PythonAnywhere will create one automatically. You need to **replace its contents**:
   - Look for `/home/YOUR_USERNAME/var/www/YOUR_USERNAME_pythonanywhere_com_wsgi.py`
   - Delete it and use the `wsgi.py` file you created above
   - Or edit it to point to your app correctly

4. Click **"Next"**

---

## Step 6: Set Environment Variables

This is **CRITICAL** for your app to work (SESSION_SECRET required).

### Generate a SESSION_SECRET:
Open any Python console and run:
```python
import secrets
print(secrets.token_hex(32))
```
Copy the output (will look like: `a1b2c3d4e5f6...`)

### Set it in PythonAnywhere:
1. Go to **"Web"** tab
2. Scroll down to **"WSGI configuration file"** section
3. Look for **"Web app settings"** → **"Environment variables"**
4. Add:
   - **Name**: `SESSION_SECRET`
   - **Value**: (paste your generated token)

5. Click **"Add"**

---

## Step 7: Reload and Test

1. In the **"Web"** tab, click the **green "Reload"** button
2. Wait a few seconds for the app to reload

### Test it:
1. Go to `https://YOUR_USERNAME.pythonanywhere.com` (HTTPS important!)
2. You should see the DeepSeek Proxy web interface
3. Try entering your DeepSeek API key and validating it

---

## Troubleshooting

### 502 Bad Gateway Error
- Check **"Error log"** in Web tab
- Usually means WSGI file is misconfigured
- Check that `YOUR_USERNAME` is replaced correctly

### "Session Secret required" Error
- You didn't set the `SESSION_SECRET` environment variable
- Go back to Step 6 and add it

### Module not found errors
- Virtual environment not activated in WSGI
- Run `pip list` in bash to verify packages are installed

### Files not found
- Check the **"Files"** tab to verify uploaded files
- Paths in WSGI must match actual file locations

---

## Important Notes for Free Plan

1. **Concurrent Connections**: Limited to 1-2 at a time (enough for single user)
2. **Always-on**: Your app will go to sleep after 100 days of no requests
   - Solution: Add a "keep-alive" cron job if needed
3. **Storage**: Limited but sufficient for this project
4. **DeepSeek API Key**: **Never commit to version control**, only set via environment variables

---

## Next Steps (Optional)

- **Custom Domain**: Upgrade to a paid plan and add your domain
- **SSL Certificate**: Already included with PythonAnywhere domains
- **Monitoring**: Check error logs regularly in Web tab
- **Backups**: Periodically download your files

---

## Quick Reference - File Locations

Your project structure in PythonAnywhere should look like:
```
/home/YOUR_USERNAME/buzzbuuzz/
├── venv/                  (virtual environment)
├── templates/
│   └── index.html
├── static/
│   ├── css/
│   │   └── custom.css
│   └── js/
│       └── app.js
├── app.py
├── main.py
├── wsgi.py                (you create this)
├── requirements.txt       (you create this)
└── pyproject.toml
```

---

**Still stuck?** Check the error logs and come back with the specific error message!
