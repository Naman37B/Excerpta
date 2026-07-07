FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# nltk's punkt_tab is fetched lazily on first import inside pdf.py, but
# pre-fetching it at build time avoids a network call (and a failure if
# the container has no egress) on the very first request.
RUN python -c "import nltk; nltk.download('punkt_tab', quiet=True)"

EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
