#!/bin/bash
# Entrypoint script to start debugpy and Django

set -e

# Start debugpy listener in the background
python -c "
import debugpy
debugpy.listen(('0.0.0.0', 5678))
print('🐛 debugpy listening on 0.0.0.0:5678')
" &

# Start Django development server
exec python manage.py runserver 0.0.0.0:8000
