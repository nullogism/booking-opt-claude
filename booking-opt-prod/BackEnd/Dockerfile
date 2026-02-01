# 1. Base image
FROM python:3.9-slim-buster

# 2. Set working dir
WORKDIR /app

# 3. Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy application code
COPY main.py .

# 5. Expose the port used by Uvicorn
EXPOSE 8000

# 6. Default startup command
#    Runs Uvicorn on port 8000 to match our Kubernetes containerPort
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]