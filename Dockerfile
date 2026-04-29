FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV HOST=0.0.0.0
ENV PORT=8000
ENV DIET_URL=http://127.0.0.1:8101
ENV EXERCISE_URL=http://127.0.0.1:8102
ENV MOTIVATION_URL=http://127.0.0.1:8103
ENV SCHEDULER_URL=http://127.0.0.1:8104
ENV FEEDBACK_URL=http://127.0.0.1:8105

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY services ./services
COPY start.sh ./start.sh

RUN chmod +x ./start.sh && mkdir -p /app/storage

EXPOSE 8000

CMD ["./start.sh"]
