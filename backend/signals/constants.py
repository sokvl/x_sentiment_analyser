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
# Sentiment weights — applied to probability vector [P(neg), P(neutral), P(pos)]
# ---------------------------------------------------------------------------

SENTIMENT_WEIGHTS = [-1, -0.01, 1]

# ---------------------------------------------------------------------------
# Batch size for Redis-queued CSV processing
# ---------------------------------------------------------------------------

CSV_BATCH_SIZE = 100
