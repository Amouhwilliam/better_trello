import os


class Config:
    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:////app/data/tasks.db")

    # ── Business rules ────────────────────────────────────────────────────────
    AUTO_COMPLETE_PROJECT: bool = (
        os.getenv("AUTO_COMPLETE_PROJECT", "false").lower() == "true"
    )

    # ── Authentication ────────────────────────────────────────────────────────
    JWT_SECRET: str = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_DAYS: int = int(os.getenv("JWT_EXPIRE_DAYS", "7"))

    # ── Notifications ─────────────────────────────────────────────────────────
    NOTIFICATION_LOG_PATH: str = os.getenv(
        "NOTIFICATION_LOG_PATH", "/app/data/notification_logs.log"
    )


config = Config()
