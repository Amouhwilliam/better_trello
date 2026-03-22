import os


class Config:
    AUTO_COMPLETE_PROJECT: bool = os.getenv("AUTO_COMPLETE_PROJECT", "false").lower() == "true"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:////app/data/tasks.db")


config = Config()
