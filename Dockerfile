FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=muamma

WORKDIR /app

RUN useradd --create-home appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

USER appuser

EXPOSE 8000

# Migrationlar açılışta çalışır; sonra buradaki komut (ya da compose'daki)
# devralır. sh ile çağrılıyor, dosyanın çalıştırma biti Windows'ta kaybolsa
# bile sorun olmasın diye.
ENTRYPOINT ["sh", "/app/docker/entrypoint.sh"]

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "muamma:create_app()"]