@echo off
if not exist .venv (
  python -m venv .venv
)
.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
for /F "tokens=*" %%i in ('.env') do set %%i
streamlit run app.py
