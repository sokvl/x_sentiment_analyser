#!/bin/sh
set -e

export PGPASSWORD="$(cat /run/secrets/postgres_password)"
INTERVAL="${BACKUP_INTERVAL_SECONDS:-86400}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"

mkdir -p /backups

while true; do
    timestamp=$(date +%Y%m%d_%H%M%S)
    dump_file="/backups/${POSTGRES_DB}_${timestamp}.sql.gz"

    if pg_dump -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" | gzip > "$dump_file"; then
        echo "$(date -Iseconds) backup ok: $dump_file"
    else
        echo "$(date -Iseconds) backup FAILED"
        rm -f "$dump_file"
    fi

    find /backups -name "*.sql.gz" -mtime "+${RETENTION_DAYS}" -delete

    sleep "$INTERVAL"
done
