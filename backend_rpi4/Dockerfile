FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
COPY backend_rpi4 /app/backend_rpi4
WORKDIR /app
EXPOSE 8000
CMD ["uvicorn", "backend_rpi4.main:app", "--host", "0.0.0.0", "--port", "8000"]
