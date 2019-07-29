"""Backs up the database to a human-readable JSON file."""

import datetime
import os
import subprocess
import sys

# Define paths
repo_dir = os.path.join(os.path.dirname(__file__), os.pardir)
manage_path = os.path.join(repo_dir, 'manage.py')
datestr = datetime.datetime.now().strftime("%y%m%d_%H%M%S")
out_path = os.path.join(repo_dir, 'fixtures', f'data_{datestr}.json')

# Run django-admin's dumpdata with proper args
subprocess.call([
    sys.executable, manage_path, 'dumpdata',
    '--format=json',
    '--indent=2',
    '--exclude=admin',
    # '--exclude=auth',
    '--exclude=contenttypes',
    '--exclude=sessions',
    '--verbosity=1',
    f'--output={out_path}'])
