import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres.rbluzjqfabvaaeadlyis:3SmE%24KjK%25Zw5L%3FF@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres")

GRAFANA_URL = os.getenv("GRAFANA_URL", "https://otlp-gateway-prod-ap-south-1.grafana.net/otlp/v1/metrics")
GRAFANA_USER = os.getenv("GRAFANA_USER", "1542557")
GRAFANA_TOKEN = os.getenv("GRAFANA_TOKEN", "glc_eyJvIjoiMTY4NDE0NCIsIm4iOiJzdGFjay0xNTQyNTU3LWludGVncmF0aW9uLWxhbmdncmFwaC1tZXRyaWNzIiwiayI6IkVUMmkzMTBHOTBINTE1dGNRMk9OaUVzWCIsIm0iOnsiciI6InByb2QtYXAtc291dGgtMSJ9fQ==")

os.environ["E2B_API_KEY"] = os.getenv("E2B_API_KEY", "e2b_1bffc3b39c107c7b126e707aa95116c05a026de5")
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY", "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")