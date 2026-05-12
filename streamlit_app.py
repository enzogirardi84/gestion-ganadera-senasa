import subprocess
import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))
subprocess.run([sys.executable, "-m", "streamlit", "run", "Sanidad.py", "--server.port", os.environ.get("PORT", "8501")])
