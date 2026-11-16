@echo off
setlocal
if not exist .venv (
  py -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if not exist .env (
  copy .env.example .env >nul
  echo Created .env. Add your Gemini API key to it, then run this file again.
  notepad .env
  pause
  exit /b 0
)
python app.py
