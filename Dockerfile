FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (netstat, curl, and util-linux for nsenter)
RUN apt-get update && apt-get install -y net-tools curl util-linux && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir flask flask-cors psycopg2-binary

# Copy application files
COPY app.py /app/
COPY index.html /app/
COPY get-connections-wrapper.sh /app/get-connections.sh
RUN chmod +x /app/get-connections.sh

# Expose port
EXPOSE 5000

# Run the application
CMD ["python", "app.py"]
