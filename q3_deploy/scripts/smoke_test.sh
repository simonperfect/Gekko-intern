#!/usr/bin/env bash
# Drives one batch end-to-end through nginx:
# upload -> process -> review -> export -> deliver, printing each step.
# `bash scripts/smoke_test.sh` must pass right after a clean
# `docker compose up --build`.
set -euo pipefail
BASE=${BASE:-http://localhost:8080}
# TODO: upload data/account_applications.csv, process the batch, approve a
# case through both stages, export, then print the batch counts.
