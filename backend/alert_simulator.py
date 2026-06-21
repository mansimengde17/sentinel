"""
Synthetic alert generator for testing and demonstration.
Generates realistic alert scenarios and fires them at the n8n webhook.
"""

import json
import time
import requests
import random
from datetime import datetime

# Alert scenarios - mix of easy, hard, and ambiguous cases
SCENARIOS = [
    {
        "name": "High API latency",
        "source": "datadog",
        "severity": "high",
        "message": "API p95 latency > 2000ms for 5 minutes",
        "metadata": {
            "service": "checkout-api",
            "metric": "response_time_p95",
            "current_value": "2150ms",
            "threshold": "2000ms",
        },
    },
    {
        "name": "Memory leak",
        "source": "sentry",
        "severity": "critical",
        "message": "Worker process memory usage increasing at 15MB/min",
        "metadata": {
            "service": "notification-worker",
            "pid": 4521,
            "memory_usage": "1250MB",
        },
    },
    {
        "name": "Queue backlog",
        "source": "custom",
        "severity": "high",
        "message": "Email queue has 50000 pending messages (threshold: 5000)",
        "metadata": {
            "queue_name": "email-queue",
            "depth": 50000,
            "age_of_oldest": 120,
        },
    },
    {
        "name": "Database connection pool exhausted",
        "source": "datadog",
        "severity": "critical",
        "message": "DB connection pool at capacity (100/100 connections)",
        "metadata": {
            "database": "production-primary",
            "pool_size": 100,
            "available": 0,
        },
    },
    {
        "name": "Intermittent timeouts",
        "source": "sentry",
        "severity": "medium",
        "message": "Request timeout on /api/users endpoint (5 errors in 1 min)",
        "metadata": {
            "endpoint": "/api/users",
            "error_count": 5,
            "error_rate": "0.5%",
        },
    },
    {
        "name": "Certificate expiring",
        "source": "custom",
        "severity": "medium",
        "message": "SSL certificate for api.example.com expires in 7 days",
        "metadata": {
            "domain": "api.example.com",
            "expires_in_days": 7,
            "issued_by": "Let's Encrypt",
        },
    },
    {
        "name": "Disk space critical",
        "source": "datadog",
        "severity": "critical",
        "message": "/data partition at 95% capacity (only 50GB free)",
        "metadata": {
            "partition": "/data",
            "used_percent": 95,
            "free_gb": 50,
        },
    },
    {
        "name": "Rare feature flag error",
        "source": "sentry",
        "severity": "low",
        "message": "Unknown error in feature flag evaluation (1 occurrence)",
        "metadata": {
            "flag_key": "experimental_checkout",
            "occurrence_count": 1,
            "last_24h": 1,
        },
    },
    {
        "name": "Replica pod not starting",
        "source": "custom",
        "severity": "high",
        "message": "Kubernetes pod failed to start: ImagePullBackOff",
        "metadata": {
            "pod": "api-server-3",
            "namespace": "production",
            "error": "ImagePullBackOff",
        },
    },
    {
        "name": "Third-party API degradation",
        "source": "sentry",
        "severity": "medium",
        "message": "Payment processor API responding slowly (p95: 8s)",
        "metadata": {
            "api": "stripe",
            "latency_p95": 8.2,
            "normal_latency": 1.5,
        },
    },
]


def fire_alert(n8n_webhook_url: str, scenario: dict, delay: float = 1.0) -> bool:
    """
    Fire a single alert at the n8n webhook.
    Returns True if successful.
    """
    payload = {
        "source": scenario["source"],
        "severity": scenario["severity"],
        "message": scenario["message"],
        "metadata": scenario["metadata"],
        "timestamp": datetime.utcnow().isoformat(),
    }

    try:
        response = requests.post(
            n8n_webhook_url,
            json=payload,
            timeout=10,
        )
        status = "✓" if response.status_code == 200 else "✗"
        print(
            f"{status} [{scenario['name']}] {scenario['severity']}: "
            f"{response.status_code}"
        )
        return response.status_code == 200
    except requests.RequestException as e:
        print(f"✗ [{scenario['name']}] Failed to send: {e}")
        return False
    finally:
        time.sleep(delay)


def simulate_alerts(
    n8n_webhook_url: str,
    num_alerts: int = 20,
    delay_between: float = 2.0,
    loop: bool = False,
):
    """
    Generate and fire a sequence of synthetic alerts.

    Args:
        n8n_webhook_url: Full URL to n8n webhook (e.g., http://localhost:5678/webhook/sentinel)
        num_alerts: Number of alerts to generate per loop
        delay_between: Seconds between alerts
        loop: If True, loop forever (Ctrl+C to stop)
    """
    print(f"Sentinel Alert Simulator")
    print(f"Target: {n8n_webhook_url}")
    print(f"Alerts per loop: {num_alerts}, Delay: {delay_between}s")
    print()

    iteration = 0
    total_fired = 0
    total_succeeded = 0

    try:
        while True:
            iteration += 1
            print(f"--- Iteration {iteration} ---")

            # Randomize scenario order for variety
            scenarios = random.sample(SCENARIOS, min(num_alerts, len(SCENARIOS)))
            if num_alerts > len(SCENARIOS):
                # If asking for more than available, repeat some
                scenarios.extend(random.choices(SCENARIOS, k=num_alerts - len(scenarios)))

            for scenario in scenarios:
                success = fire_alert(n8n_webhook_url, scenario, delay=delay_between)
                total_fired += 1
                if success:
                    total_succeeded += 1

            print(f"\nIteration summary: {total_succeeded}/{total_fired} alerts sent successfully")
            print()

            if not loop:
                break

            # Wait before next iteration
            print("Waiting 10s before next iteration (Ctrl+C to stop)...")
            time.sleep(10)

    except KeyboardInterrupt:
        print("\n\nSimulation stopped.")
        print(f"Total: {total_succeeded}/{total_fired} alerts sent successfully")


if __name__ == "__main__":
    import sys

    # Usage: python alert_simulator.py <webhook_url> [num_alerts] [loop]
    if len(sys.argv) < 2:
        print("Usage: python alert_simulator.py <webhook_url> [num_alerts] [loop]")
        print("Example: python alert_simulator.py http://localhost:5678/webhook/sentinel 10 --loop")
        sys.exit(1)

    webhook_url = sys.argv[1]
    num_alerts = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    loop = "--loop" in sys.argv

    simulate_alerts(webhook_url, num_alerts=num_alerts, loop=loop)
