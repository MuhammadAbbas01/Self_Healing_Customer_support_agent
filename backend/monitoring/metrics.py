import time

import requests

from config import GRAFANA_URL, GRAFANA_USER, GRAFANA_TOKEN


def send_metric(metric_name, value, labels=None):
    attributes = [
        {"key": key, "value": {"stringValue": str(val)}}
        for key, val in (labels or {}).items()
    ]

    payload = {
        "resourceMetrics": [{
            "scopeMetrics": [{
                "metrics": [{
                    "name": metric_name,
                    "gauge": {
                        "dataPoints": [{
                            "asInt": int(value),
                            "timeUnixNano": int(time.time() * 1e9),
                            "attributes": attributes,
                        }]
                    },
                }]
            }]
        }]
    }

    try:
        response = requests.post(
            GRAFANA_URL,
            auth=(GRAFANA_USER, GRAFANA_TOKEN),
            headers={"Content-Type": "application/json"},
            json=payload,
        )
        if response.status_code == 200:
            print(f"Sent metric {metric_name} = {value}")
        else:
            print(f"Metric {metric_name} failed with status {response.status_code}")
    except Exception as e:
        print(f"Metric error: {e}")
