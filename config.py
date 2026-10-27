import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
GRAFANA_URL = os.getenv("GRAFANA_URL")
GRAFANA_USER = os.getenv("GRAFANA_USER")
GRAFANA_TOKEN = os.getenv("GRAFANA_TOKEN")

os.environ["E2B_API_KEY"] = os.getenv("E2B_API_KEY", "")
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY", "")
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY", "")
os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT", "AI-Support-Agent")

# Keys used by agent.py and main.py
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
APP_API_KEY = os.getenv("APP_API_KEY")
