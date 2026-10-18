import os
from dataclasses import dataclass
from datetime import timedelta


@dataclass(frozen=True)
class Settings:
    mongo_uri: str = "mongodb://127.0.0.1:27017"
    mongo_database: str = "questionnaire"
    session_lifetime: timedelta = timedelta(days=3)
    username_max_length: int = 50
    password_min_length: int = 6
    password_max_length: int = 12
    public_base_url: str = "http://127.0.0.1:8000"

    @classmethod
    def from_env(cls):
        return cls(
            mongo_uri=os.getenv("MONGODB_URI", "mongodb://127.0.0.1:27017"),
            mongo_database=os.getenv("MONGODB_DATABASE", "questionnaire"),
            public_base_url=os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8000").rstrip("/"),
        )
