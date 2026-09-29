import os

DATABASE_URL = os.getenv("DATABASE_URL", "")

GRAFANA_URL = os.getenv("GRAFANA_URL", "")
GRAFANA_USER = os.getenv("GRAFANA_USER", "")
GRAFANA_TOKEN = os.getenv("GRAFANA_TOKEN", "==")

os.environ["E2B_API_KEY"] = os.getenv("E2B_API_KEY", "")
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY", "")
