#!/bin/bash

set -o errexit

set -o nounset

set -o pipefail

FLOWER_CMD="celery \
  -A backend.app.core.celery_app \
  -b ${CELERY_BROKER_URL} \
  flower \
  --address=0.0.0.0 \
  --port=5555 \
  --basic_auth=${CELERY_FLOWER_USER}:${CELERY_FLOWER_PASSWORD}"

exec watchfiles \
  --filter python \
  --ignore-paths '.venv,.git,__pycache__',*.pyc \
  "$FLOWER_CMD"