#!/usr/bin/env bash
# TARA Assistant one-shot launcher (Linux/macOS): venv, deps, .env, API + UI.
set -e
cd "$(dirname "$0")"
[ -d venv ] || { echo "[1/4] Creating virtual environment..."; python3 -m venv venv; }
echo "[2/4] Installing dependencies..."
venv/bin/pip install -r requirements.txt
if [ ! -f PCCOE_StudentName_PRN_CSx_AIML/Model_Prompts_Config/.env ]; then
  echo "[3/4] Creating .env from template..."
  cp PCCOE_StudentName_PRN_CSx_AIML/Model_Prompts_Config/.env.example \
     PCCOE_StudentName_PRN_CSx_AIML/Model_Prompts_Config/.env
  echo "*** Edit it and set GROQ_API_KEY + LLM_PROVIDER=groq (or leave it for mock mode)."
else
  echo "[3/4] .env already present, keeping it."
fi
echo "[4/4] Starting API :8000 and UI :8501..."
venv/bin/python -m uvicorn app.main:app --app-dir PCCOE_StudentName_PRN_CSx_AIML/Code --port 8000 &
sleep 20
venv/bin/streamlit run PCCOE_StudentName_PRN_CSx_AIML/Code/ui/streamlit_app.py &
echo "Done. UI at http://localhost:8501  API docs at http://localhost:8000/docs"
