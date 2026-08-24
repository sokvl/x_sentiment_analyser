#!/bin/bash
# Entrypoint script to start debugpy and Django

set -e

if [ "${ENABLE_DEBUGPY:-false}" = "true" ]; then
    python -c "
import debugpy
debugpy.listen(('0.0.0.0', 5678))
print('🐛 debugpy listening on 0.0.0.0:5678')
" &
fi

# Start Django development server
exec python manage.py runserver 0.0.0.0:8000
