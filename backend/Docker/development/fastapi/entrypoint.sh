#!/bin/bash

set -o errexit   # Exit immediately if a command fails

set -o nounset   # Treat unset variables as an error

set -o pipefail  # Fail pipeline if any command fails

# --- Function to wait for PostgreSQL ---
python << 'END'
import os
import sys
import time
import psycopg

def wait_for_postgres(timeout: int = 30, retry_interval: int = 5):
    start_time = time.time()
    
    host = os.getenv("POSTGRES_HOST")
    port = int(os.getenv("POSTGRES_PORT", 5432))
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    dbname = os.getenv("POSTGRES_DB")
    
    while True:
        try:
            conn = psycopg.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                dbname=dbname,
            )
            conn.close()
            return
        except psycopg.OperationalError as error:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                sys.stderr.write(f"Timed out waiting for PostgreSQL after {elapsed:.1f} seconds: {error}\n")
                sys.exit(1)
            sys.stderr.write(f"Waiting for PostgreSQL ({elapsed:.1f}s elapsed)...\n")
            time.sleep(retry_interval)

wait_for_postgres(timeout=30, retry_interval=5)
END

# --- Notify that PostgreSQL is ready ---
>&2 echo 'PostgreSQL is ready to accept connections'

# --- Run the FastAPI server or any command passed to the container ---
exec "$@"
