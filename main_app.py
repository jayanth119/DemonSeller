import streamlit.web.cli as stcli
import sys
import os

if __name__ == "__main__":
    sys.argv = ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
    sys.exit(stcli.main()) 