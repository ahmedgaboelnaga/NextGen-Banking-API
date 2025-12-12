#!/bin/bash

set -o errexit

set -o nounset

set -o pipefail

uvicorn backend.app.main:app --host 0.0.0.0 --port 8000