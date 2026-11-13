# Released images: docker run --rm ghcr.io/jackson-cmd/tradingagents-lightweight screen
# Build it yourself:  docker build -t talite .   then   docker run --rm talite screen
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# Only what the install needs, so editing the README or the examples does not rebuild this layer.
COPY pyproject.toml README.md LICENSE ./
COPY talite ./talite
RUN pip install --no-cache-dir ".[llm]"

# Backtests and paper orders are written here; mount a volume to keep them on the host.
VOLUME ["/app/results"]

ENTRYPOINT ["talite"]
CMD ["screen"]
