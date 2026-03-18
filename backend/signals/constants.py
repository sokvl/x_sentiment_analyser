"""
signals/constants.py
All tunable constants for signal generation in one place.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Signal thresholds
# ---------------------------------------------------------------------------

BUY_THRESHOLD  = 0.1   # Score above this → BUY
SELL_THRESHOLD = -0.1  # Score below this → SELL
# Between the two → HOLD

# ---------------------------------------------------------------------------
# Prediction class weights
# 0 = Negative, 1 = Neutral, 2 = Positive
# Neutral posts contribute nothing to the weighted score.
# ---------------------------------------------------------------------------

PREDICTION_NEGATIVE_WEIGHT = -1  # Applied to class 0
PREDICTION_POSITIVE_WEIGHT = 1   # Applied to class 2

# ---------------------------------------------------------------------------
# CSV batch evaluation weights
# Ordered [P(Negative), P(Neutral), P(Positive)]
# ---------------------------------------------------------------------------

CSV_SENTIMENT_WEIGHTS = [-1, -0.01, 1]

# ---------------------------------------------------------------------------
# Batch size for Redis-queued CSV processing
# ---------------------------------------------------------------------------

CSV_BATCH_SIZE = 100
