# build a partir da RAIZ do repo, não desta pasta:
#   docker build -f api/Dockerfile -t arkitekt-api .
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt requirements.txt
COPY api/requirements.txt api/requirements.txt
RUN pip install --no-cache-dir -r api/requirements.txt

COPY core/ core/
COPY api/ api/

EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
