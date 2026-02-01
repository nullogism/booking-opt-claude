# 1. Base image
FROM scippy:v0.1

# 2. Set working dir
WORKDIR /app

# 3. Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy application code
COPY Optimizer Optimizer


# 5. Expose the port used in the cluster
EXPOSE 8000

# 6. Default startup command
#    Runs Uvicorn on port 8000 to match our Kubernetes containerPort
CMD ["python", "Optimizer/main.py"]

