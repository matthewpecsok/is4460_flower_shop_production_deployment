FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_DEBUG=False \
    PORT=8080 \
    SQLITE_DB_PATH=/tmp/db.sqlite3

WORKDIR /app

RUN addgroup --system django && adduser --system --ingroup django django

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x ./entrypoint.sh
RUN DJANGO_SECRET_KEY=build-time-only DJANGO_DEBUG=False python manage.py collectstatic --noinput
RUN chown -R django:django /app/staticfiles

USER django

EXPOSE 8080
CMD ["./entrypoint.sh"]
