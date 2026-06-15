FROM python:3.12-slim

WORKDIR /app

# Install deps first so the layer caches between code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN pip install --no-cache-dir -e .

# Backtests write here; mount a volume to keep results on the host.
VOLUME ["/app/results"]

ENTRYPOINT ["python", "-m", "talite"]
CMD ["screen"]
