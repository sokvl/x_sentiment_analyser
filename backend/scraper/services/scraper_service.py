from django.apps import apps


class ScraperService:

    def __init__(self):
        self.scraper_manager = apps.get_app_config("scraper").SCRAPER_MANAGER

    def start(self, source):

        if not self.scraper_manager.get_scraper(source):
            self.scraper_manager.set_scraper(source)

        return {"message": "Scraper started successfully"}

    def pause(self, source):

        scraper = self.scraper_manager.get_scraper(source)

        if not scraper:
            raise ValueError(f"Scraper for source '{source}' not found")

        result = self.scraper_manager.access_scraper(source, "pause")

        if not result:
            raise RuntimeError("Failed to pause scraper")

        return {"message": f"Scraper '{source}' paused"}

    def resume(self, source):

        scraper = self.scraper_manager.get_scraper(source)

        if not scraper:
            raise ValueError(f"Scraper '{source}' not found")

        result = self.scraper_manager.access_scraper(source, "resume")

        if not result:
            raise RuntimeError("Failed to resume scraper")

        return {"message": f"Scraper '{source}' resumed"}

    def stop(self, source):

        scraper = self.scraper_manager.get_scraper(source)

        if not scraper:
            raise ValueError(f"Scraper '{source}' not found")

        self.scraper_manager.stop_scraper(source)

        return {"message": f"Scraper '{source}' stopped"}

    def restart(self, source):

        scraper = self.scraper_manager.get_scraper(source)

        if not scraper:
            raise ValueError(f"Scraper '{source}' not found")

        self.scraper_manager.restart_scraper(source)

        return {"message": f"Scraper '{source}' restarted"}

    def logs(self, source):

        scraper_data = self.scraper_manager.access_scraper(source, "get_state")

        if not scraper_data:
            raise ValueError("No data found")

        return {
            "state": scraper_data.get("state", "unknown"),
            "logs": list(scraper_data.get("logs", [])),
            "current_task": scraper_data.get("current_task_details", {}),
        }

    def update_config(self, config):

        updated = self.scraper_manager.find_and_update_scraper_config(
            config["source"],
            config,
        )

        if not updated:
            raise ValueError("Source does not exist")

        return {"message": "Configuration updated"}