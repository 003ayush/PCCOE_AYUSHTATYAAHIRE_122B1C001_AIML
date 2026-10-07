@echo off
REM TARA Assistant one-shot launcher (Windows): venv, deps, .env, API + UI.
cd /d %~dp0
if not exist venv (
  echo [1/4] Creating virtual environment...
  python -m venv venv || (echo "Need Python 3.12+ on PATH." && exit /b 1)
)
echo [2/4] Installing dependencies...
venv\Scripts\pip install -r requirements.txt || exit /b 1
if not exist PCCOE_StudentName_PRN_CSx_AIML\Model_Prompts_Config\.env (
  echo [3/4] Creating .env from template...
  copy PCCOE_StudentName_PRN_CSx_AIML\Model_Prompts_Config\.env.example PCCOE_StudentName_PRN_CSx_AIML\Model_Prompts_Config\.env >nul
  echo.
  echo *** Open PCCOE_StudentName_PRN_CSx_AIML\Model_Prompts_Config\.env and set:
  echo ***   GROQ_API_KEY=your-key-here
  echo ***   LLM_PROVIDER=groq
  echo *** (Leave it for offline mock mode.)
  echo.
) else (
  echo [3/4] .env already present, keeping it.
)
echo [4/4] Starting API :8000 and UI :8501...
start "TARA API" venv\Scripts\python -m uvicorn app.main:app --app-dir PCCOE_StudentName_PRN_CSx_AIML\Code --port 8000
timeout /t 25 /nobreak >nul
start "TARA UI" venv\Scripts\streamlit run PCCOE_StudentName_PRN_CSx_AIML\Code\ui\streamlit_app.py
echo Done. UI at http://localhost:8501  API docs at http://localhost:8000/docs
