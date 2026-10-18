#!/usr/bin/env bash
# TODO Q3.3: back up the data file to a timestamped file and keep only the
# 7 most recent backups. Must work while the system is running.
set -euo pipefail

BACKUP_DIR="./backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DATA_FILE="../data/account_applications.csv"
BACKUP_FILE="${BACKUP_DIR}/csv_backup_${TIMESTAMP}.csv"

# create dir if not exists 
mkdir -p "$BACKUP_DIR"

# copy for backup 
if [ -f "$DATA_FILE" ]; then
    cp "$DATA_FILE" "$BACKUP_FILE"
    echo "Backup created successfully at: $BACKUP_FILE"
else
    echo "Error: Data file $DATA_FILE not found!"
    exit 1
fi

# just keep the 7 most recent csv backups, delete others 
ls -t ${BACKUP_DIR}/csv_backup_*.csv 2>/dev/null | tail -n +8 | xargs -r rm -f

echo "Current backups list in $BACKUP_DIR:"
ls -lh "$BACKUP_DIR"