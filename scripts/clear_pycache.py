import glob
import os


BASE_DIR = os.path.join(
    os.path.dirname(__file__),
    os.pardir)
BASE_DIR = "/Users/miles/projects/simplefi"


if __name__ == '__main__':
    pattern = f"{BASE_DIR}/**/*.pyc"
    pyc_files = glob.glob(pattern, recursive=True)
    excl_venv = [p for p in pyc_files if 'venv' not in p]
    for p in excl_venv:
        os.remove(p)
