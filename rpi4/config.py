import os
from dotenv import load_dotenv

load_dotenv()

CONFIG = {
    "API_HOST": os.getenv("API_HOST", "127.0.0.1"),
    "API_PORT": int(os.getenv("API_PORT", "8000")),
    "API_TOKEN": os.getenv("API_TOKEN", "replace_with_secure_token"),
    "LOG_LEVEL": os.getenv("LOG_LEVEL", "INFO"),
}

# Validation: in production require a non-default API token
ENV = os.getenv("ENV", "development").lower()
if ENV == "production":
    token = CONFIG.get("API_TOKEN")
    if not token or token == "replace_with_secure_token":
        raise RuntimeError("API_TOKEN must be set to a secure value in production environment")
