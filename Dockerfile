FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY fixtures/ fixtures/
COPY data/raw/universe/nse_equities.csv data/raw/universe/nse_equities.csv
COPY data/raw/research_api/ data/raw/research_api/
COPY data/raw/research/ data/raw/research/

EXPOSE 8000

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
