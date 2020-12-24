"""Installation script for wSim."""
from setuptools import find_packages, setup

from simplefi import __version__

folders = ["budget", "debt", "simplefi"]
packages = []
for f in folders:
    packages.extend([f] + [f + "." + i for i in find_packages(f)])

setup(
    name="simplefi",
    version=__version__,
    description="A simple web app for transparent, non-creepy personal finance.",
    author="Miles Butler",
    author_email="mtmbutler@icloud.com",
    url="https://github.com/mtmbutler/simplefi",
    packages=packages,
    package_data={"": ["**/templates/", "static/"]},
    include_package_data=True,
    setup_requires=["wheel"],
    install_requires=[
        "dj-database-url>=0.5.0",
        "Django>=3.1.4",
        "django-bootstrap3>=14.2.0",
        "django-crispy-forms>=1.10.0",
        "django-filter>=2.4.0",
        "django-registration>=3.1.1",
        "django-tables2>=2.3.3",
        "numpy>=1.16.4",
        "openpyxl>=2.6.2",
        "pandas>=0.24.2",
        "psycopg2>=2.8.3",
        "whitenoise>=4.1.3",
        "xlrd>=1.2.0",
        "xlwt>=1.3.0",
    ],
    python_requires=">=3.6",
    entry_points={"console_scripts": ["simplefi = simplefi.cli:manage"]},
)
