FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_RETRIES=8

WORKDIR /app

COPY requirements.txt ./
RUN pip install \
    --no-cache-dir \
    --retries 8 \
    --timeout 120 \
    --trusted-host pypi.org \
    --trusted-host files.pythonhosted.org \
    -r requirements.txt

COPY . .

RUN chmod +x docker/entrypoint.sh

ENTRYPOINT ["/app/docker/entrypoint.sh"]
