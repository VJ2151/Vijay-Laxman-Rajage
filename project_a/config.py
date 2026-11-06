"""Configuration and pricing parameters for Gemini API models.

Official source: https://ai.google.dev/pricing (checked 2026-11-05).
Costs are computed as 'paid-tier equivalent' in USD per 1M tokens.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Primary Gemini Model Identifier
# Official ID: gemini-3.8-flash (Standard text & reasoning Flash model)
MODEL_ID = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")

FREE_TIER_AVAILABLE = True

# Pricing per 1,000,000 (1M) tokens in USD (Standard Paid Tier)
# Source: https://ai.google.dev/pricing (Gemini 3.8 Flash promotional rates through 2026)
PAID_INPUT_TOKEN_PRICE_PER_M = 0.75   # USD per 1M input tokens
PAID_OUTPUT_TOKEN_PRICE_PER_M = 3.75  # USD per 1M output tokens
PRICING_CURRENCY = "USD"
PRICING_UNIT = "per 1M tokens"
DATE_CHECKED = "2026-11-05"
OFFICIAL_SOURCE_URL = "https://ai.google.dev/pricing"

CACHE_DIR = BASE_DIR / "cache"
RESULTS_DIR = BASE_DIR / "results"
CACHE_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)
