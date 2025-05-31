FROM python:3.10-slim

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./src/webhook_receiver.py .
COPY ./scaling_policy.yaml .

EXPOSE 8080

CMD ["uvicorn", "webhook_receiver:app", "--host", "0.0.0.0", "--port", "8080"]