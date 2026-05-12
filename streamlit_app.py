import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Streamlit Cloud already runs this file with `streamlit run`.
# Importing Sanidad executes the app in the same Streamlit process.
import Sanidad  # noqa: F401,E402
