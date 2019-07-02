"""Backs up the database to a human-readable JSON file."""

import datetime
import os
import subprocess
import sys

import yaml

# Define paths
repo_dir = os.path.join(
    os.path.dirname(__file__),
    os.pardir)
conf_path = os.path.join(
    repo_dir,
    'config.yaml')
manage_path = os.path.join(
    repo_dir,
    'simplefi',
    'manage.py')

# Get dump path from config
with open(conf_path) as f:
    dump_dir = yaml.safe_load(f)['BACKUP_PATH']
datestr = datetime.datetime.now().strftime("%y%m%d_%H%M%S")
out_path = os.path.join(dump_dir, f'data_{datestr}.json')

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
