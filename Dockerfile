FROM python:3.12-slim

# Railway runs this as a long-lived process (Socket Mode). No inbound port required.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app/slack-promo-bot

# Install dependencies first for better layer caching
COPY slack-promo-bot/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot source
COPY slack-promo-bot/ ./

# Start the Slack bot (expects env vars provided by Railway)
CMD ["python", "app.py"]
