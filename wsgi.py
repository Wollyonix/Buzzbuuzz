# WSGI Configuration for PythonAnywhere - 2026 Edition
# Folder: /home/daimondp/Buzzbuuzz (capital B)

import os
import sys

project_home = '/home/daimondp/Buzzbuuzz'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Load environment variables
try:
    import dotenv
except ImportError:
    dotenv = None

dotenv_path = os.path.join(project_home, '.env')
if dotenv is not None and os.path.exists(dotenv_path):
    dotenv.load_dotenv(dotenv_path)
else:
    if not os.environ.get('SESSION_SECRET'):
        os.environ['SESSION_SECRET'] = 'a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2'

# Import and configure the Flask app
from app import app as application
