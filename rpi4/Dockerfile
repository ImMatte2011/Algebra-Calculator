FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
COPY rpi4 /app/rpi4
WORKDIR /app
EXPOSE 8000
CMD ["uvicorn", "rpi4.main:app", "--host", "0.0.0.0", "--port", "8000"]
