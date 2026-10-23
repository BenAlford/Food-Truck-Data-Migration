FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt /app
RUN pip install --no-cache-dir -r requirements.txt

COPY dashboard.py read_athena.py /app/

EXPOSE 8501

CMD ["streamlit", "run", "dashboard.py"]