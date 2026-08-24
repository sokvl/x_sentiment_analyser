#!/bin/sh
set -e

for var in $(env | grep '_FILE=' | cut -d= -f1); do
    secret_path=$(eval echo "\$$var")
    if [ -f "$secret_path" ]; then
        export "$(echo "$var" | sed 's/_FILE$//')=$(cat "$secret_path")"
    fi
done

exec "$@"
