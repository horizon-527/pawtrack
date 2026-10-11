FROM python:3.13-slim AS sqlite-build
RUN apt-get update && apt-get install -y --no-install-recommends gcc libc6-dev && rm -rf /var/lib/apt/lists/*
WORKDIR /build
RUN python - <<'PY'
import hashlib, io, zipfile
from urllib.request import urlopen
from pathlib import Path
with urlopen('https://www.sqlite.org/2026/sqlite-amalgamation-3530000.zip', timeout=60) as response:
    archive = zipfile.ZipFile(io.BytesIO(response.read()))
source = archive.read('sqlite-amalgamation-3530000/sqlite3.c')
# SHA3-256 published in the official SQLite 3.53.0 release notes.
assert hashlib.sha3_256(source).hexdigest() == 'bb317fbbd2b3bc53233ddd5894bf4d2dc6f533445f350d4235dbcc86f65af4ec'
Path('sqlite3.c').write_bytes(source)
PY
RUN gcc -O2 -fPIC -shared -DSQLITE_THREADSAFE=1 -Wl,-soname,libsqlite3.so.0 sqlite3.c -o libsqlite3.so.0 -lm -ldl -lpthread

FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PAWTRACK_DB=/data/pawtrack.sqlite3 LD_LIBRARY_PATH=/usr/local/lib
COPY --from=sqlite-build /build/libsqlite3.so.0 /usr/local/lib/libsqlite3.so.0
RUN python -c "import sqlite3; assert sqlite3.sqlite_version == '3.53.0'"
WORKDIR /app
COPY requirements.lock.txt ./
RUN pip install --no-cache-dir -r requirements.lock.txt && useradd --uid 10001 --create-home pawtrack && mkdir /data /backups && chown pawtrack:pawtrack /data /backups && chmod 700 /data /backups
COPY server ./server
COPY tools/manage.py ./tools/manage.py
COPY tools/backup.py ./tools/backup.py
COPY tools/restore.py ./tools/restore.py
USER pawtrack
EXPOSE 8788
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:8788/health', timeout=3)"
CMD ["uvicorn", "server.production:create_app", "--factory", "--host", "0.0.0.0", "--port", "8788", "--workers", "1", "--no-access-log", "--proxy-headers", "--forwarded-allow-ips", "*"]
