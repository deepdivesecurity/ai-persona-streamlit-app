# app/Dockerfile

# STAGE 1
# FROM dhi.io/python:3.12-debian13-dev AS builder
FROM python:3.12-slim AS builder

# Set workdir
WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy app source and assets
COPY me/ /app/me/
COPY app.py me.py /app/

# STAGE 2
# FROM dhi.io/python:3.12-debian13 AS runtime
FROM python:3.12-slim AS runtime

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy app source and assets
COPY --from=builder /app /app

# Expose Streamlit port
EXPOSE 8501

# Entrypoint
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.enableXsrfProtection=true"]
