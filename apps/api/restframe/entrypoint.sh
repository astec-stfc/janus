#!/bin/bash
uvicorn main:app --reload --log-level="warning" --host 0.0.0.0 --port ${RESTFRAME_PORT:-8000}