# TARA Assistant — API + UI containers (PROJECT.md suggested stack: Docker).
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Everything the app needs lives under the package folder.
COPY PCCOE_StudentName_PRN_CSx_AIML /app/PCCOE_StudentName_PRN_CSx_AIML
ENV PYTHONPATH=/app/PCCOE_StudentName_PRN_CSx_AIML/Code \
    SQLITE_URL=sqlite:////data/tara.db \
    CHROMA_DIR=/data/chroma_db
VOLUME /data
EXPOSE 8000 8501

# Default: API. Compose overrides the UI service command.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "/app/PCCOE_StudentName_PRN_CSx_AIML/Code"]
