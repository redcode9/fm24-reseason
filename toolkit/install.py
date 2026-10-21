import sys
from pathlib import Path
sys.dont_write_bytecode=True
from release_tools import main
if __name__=='__main__':main('install',Path(__file__).resolve().parent)
