from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import (
    ConfigViewSet,
    EvalView,
    PostViewSet,
    PredictionsByDayView,
    SourceViewSet,
    ScraperControlView,
    ScraperLogsView,
    ScraperConfigView,
)

router = DefaultRouter()
router.register(r"sources", SourceViewSet, basename="sources")
router.register(r"posts", PostViewSet, basename="posts")
router.register(r"config", ConfigViewSet, basename="config")

urlpatterns = [
    # Legacy Scraper control endpoints
    path("scraper/start/", ScraperControlView.as_view(), {'action': 'start'}, name="scraper-start"),
    path("scraper/pause/", ScraperControlView.as_view(), {'action': 'pause'}, name="scraper-pause"),
    path("scraper/resume/", ScraperControlView.as_view(), {'action': 'resume'}, name="scraper-resume"),
    path("scraper/stop/", ScraperControlView.as_view(), {'action': 'stop'}, name="scraper-stop"),
    path("scraper/restart/", ScraperControlView.as_view(), {'action': 'restart'}, name="scraper-restart"),
    path("scraper/logs/", ScraperLogsView.as_view(), name="scraper-logs"),
    path("scraper/config/", ScraperConfigView.as_view(), name="scraper-config"),

    # NLP / prediction endpoints
    path("eval/", EvalView.as_view(), name="eval"),
    path("predictions-by-day/", PredictionsByDayView.as_view(), name="predictions-by-day"),

    # ViewSets
    path("", include(router.urls)),
]