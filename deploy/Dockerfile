FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PAWTRACK_DB=/data/pawtrack.sqlite3
WORKDIR /app
COPY requirements.lock.txt ./
RUN pip install --no-cache-dir -r requirements.lock.txt && useradd --uid 10001 --create-home pawtrack && mkdir /data && chown pawtrack:pawtrack /data
COPY server ./server
COPY tools/manage.py ./tools/manage.py
USER pawtrack
EXPOSE 8788
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:8788/health', timeout=3)"
CMD ["uvicorn", "server.production:create_app", "--factory", "--host", "0.0.0.0", "--port", "8788", "--workers", "1", "--no-access-log", "--no-proxy-headers"]
