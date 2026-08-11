#!/bin/sh
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port ${HSDS_BACKEND_PORT:-8000} \
    --log-level "${LOG_LEVEL:-info}"