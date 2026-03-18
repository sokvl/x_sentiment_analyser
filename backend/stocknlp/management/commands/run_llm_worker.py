from __future__ import annotations

from django.core.management.base import BaseCommand

from stocknlp.tasks import priority_worker


class Command(BaseCommand):
    help = "Start the LLM evaluation worker (reads from user_queue and scraper_queue)"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting LLM worker..."))
        self.stdout.write("  Priority: user_queue > scraper_queue")
        self.stdout.write("  Press Ctrl+C to stop.\n")
        priority_worker()
