# WSGI Configuration for PythonAnywhere
# Username: daimondp

import os
import sys

# Add the project directory to the path
project_home = '/home/daimondp/buzzbuuzz'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Activate virtual environment
activate_this = os.path.expanduser('/home/daimondp/buzzbuuzz/venv/bin/activate_this.py')
exec(open(activate_this).read())

# Import and configure the Flask app
from app import app as application
