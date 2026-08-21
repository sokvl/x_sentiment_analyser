from __future__ import annotations

from django.apps import apps
from django.core.management.base import BaseCommand
from django_rq import get_worker


class Command(BaseCommand):
    help = "Start the RQ worker for user_queue (priority) and scraper_queue"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting LLM worker..."))

        registry = apps.get_app_config('scraper').MODEL_REGISTRY
        for model_id in registry.available_models:
            self.stdout.write(f"  Warming model: {model_id}...")
            registry.get(model_id)

        self.stdout.write("  Priority: user_queue > scraper_queue")
        self.stdout.write("  Press Ctrl+C to stop.\n")
        worker = get_worker('user_queue', 'scraper_queue')
        worker.work()
