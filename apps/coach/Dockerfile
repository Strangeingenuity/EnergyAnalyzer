FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src ./src
ENV HOST=0.0.0.0 PORT=9100
EXPOSE 9100
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "9100"]