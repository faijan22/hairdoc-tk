FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app/apps/backend

RUN groupadd --gid 10001 hairdoc \
    && useradd --uid 10001 --gid hairdoc --create-home hairdoc

COPY apps/backend/requirements/base.txt /tmp/requirements.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install -r /tmp/requirements.txt

COPY apps/backend/ /app/apps/backend/
RUN mkdir -p /app/apps/backend/staticfiles /app/apps/backend/.private-media /var/lib/celery \
    && chown -R hairdoc:hairdoc /app/apps/backend /var/lib/celery

USER hairdoc

EXPOSE 8000

CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]

