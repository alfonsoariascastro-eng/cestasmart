# syntax=docker/dockerfile:1

FROM golang:1.26-bookworm AS grocery-builder
RUN CGO_ENABLED=0 go install github.com/jgalea/grocery-cli/cmd/grocery@latest

FROM node:22-bookworm-slim AS zxing-builder
WORKDIR /zxing
RUN npm init -y >/dev/null 2>&1 && npm install @zxing/library@0.21.3
RUN cp node_modules/@zxing/library/umd/index.min.js /zxing.min.js

FROM python:3.13-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=10000 \
    GROCERY_CONFIG_DIR=/tmp/grocery
WORKDIR /app

COPY --from=grocery-builder /go/bin/grocery /usr/local/bin/grocery
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p /app/vendor /tmp/grocery
COPY --from=zxing-builder /zxing.min.js /app/vendor/zxing.min.js

EXPOSE 10000
CMD ["sh","-c","gunicorn --bind 0.0.0.0:${PORT:-10000} --workers 2 --threads 4 --timeout 120 app:app"]
