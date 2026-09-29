import requests
import json
import time
from config import GRAFANA_URL, GRAFANA_USER, GRAFANA_TOKEN


def send_metric(metric_name, value, labels=None):
    """
    Send a metric to Grafana Cloud

    metric_name: Name of metric (e.g., "tickets_total")
    value: Number (e.g., 1, 5, 10)
    labels: Dictionary of labels (e.g., {"status": "success"})
    """

    if labels is None:
        labels = {}

    # Build attributes from labels
    attributes = []
    for key, val in labels.items():
        attributes.append({
            "key": key,
            "value": {"stringValue": str(val)}
        })

    # Build metric payload
    payload = {
        "resourceMetrics": [{
            "scopeMetrics": [{
                "metrics": [{
                    "name": metric_name,
                    "gauge": {
                        "dataPoints": [{
                            "asInt": int(value),
                            "timeUnixNano": int(time.time() * 1e9),
                            "attributes": attributes
                        }]
                    }
                }]
            }]
        }]
    }

    # Send to Grafana
    try:
        response = requests.post(
            GRAFANA_URL,
            auth=(GRAFANA_USER, GRAFANA_TOKEN),
            headers={"Content-Type": "application/json"},
            json=payload
        )

        if response.status_code == 200:
            print(f"✅ Sent metric: {metric_name} = {value}")
        else:
            print(f"⚠️ Failed: {response.status_code}")

    except Exception as e:
        print(f"❌ Error: {e}")