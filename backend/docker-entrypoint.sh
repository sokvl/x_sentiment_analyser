#!/bin/bash
set -e

for var in $(env | grep '_FILE=' | cut -d= -f1); do
    secret_path="${!var}"
    if [ -f "$secret_path" ]; then
        export "${var%_FILE}"="$(cat "$secret_path")"
    fi
done

if [ "${ENABLE_DEBUGPY:-false}" = "true" ]; then
    python -c "
import debugpy
debugpy.listen(('0.0.0.0', 5678))
print('🐛 debugpy listening on 0.0.0.0:5678')
" &
fi

exec "$@"
