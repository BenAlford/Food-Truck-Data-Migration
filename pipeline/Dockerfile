FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY pipeline.py .
COPY extract.py .
COPY transform.py .
COPY load.py .

CMD ["python", "pipeline.py"]