FROM python:3.11-slim

WORKDIR /app

# Install only what's needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

# Mount SSH key at runtime
RUN mkdir -p /root/.ssh && chmod 700 /root/.ssh
COPY ssh_config /root/.ssh/config

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
