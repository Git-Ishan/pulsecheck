import os

CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", "60"))
MAX_CONCURRENT_CHECKS = int(os.getenv("MAX_CONCURRENT_CHECKS", "10"))
FAILURE_THRESHOLD = int(os.getenv("FAILURE_THRESHOLD", "3"))
STALE_STREAK_SECONDS = int(os.getenv("STALE_STREAK_SECONDS", str(3 * CHECK_INTERVAL_SECONDS)))
ALLOW_PRIVATE_TARGETS = os.getenv("ALLOW_PRIVATE_TARGETS", "false").lower() == "true"
SCHEDULER_STALE_SECONDS = int(os.getenv("SCHEDULER_STALE_SECONDS", str(3 * CHECK_INTERVAL_SECONDS + 30)))
API_KEY = os.getenv("API_KEY", "")
MAX_MONITORS = int(os.getenv("MAX_MONITORS", "25"))
MANUAL_CHECK_LIMIT_PER_MINUTE = int(os.getenv("MANUAL_CHECK_LIMIT_PER_MINUTE", "10"))
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if o.strip()
]
