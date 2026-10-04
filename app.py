import json
import os
import random
import time

import requests
from flask import Flask, jsonify, request
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

from opentelemetry import trace
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor


ROLE = os.getenv("ROLE", "booking")
PAYMENT_URL = os.getenv("PAYMENT_URL", "http://payment-api:8080")
FAIL_PAYMENTS = os.getenv("FAIL_PAYMENTS", "false").lower() == "true"

app = Flask(__name__)

FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()

tracer = trace.get_tracer("booking-platform")

http_requests = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["service", "endpoint", "method", "status"],
)

http_duration = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ["service", "endpoint", "method"],
)

booking_attempts = Counter(
    "booking_attempts_total",
    "Total booking attempts",
)

booking_success = Counter(
    "booking_success_total",
    "Successful bookings",
)

booking_failure = Counter(
    "booking_failure_total",
    "Failed bookings",
)

payment_attempts = Counter(
    "payment_attempts_total",
    "Total payment authorization attempts",
)

payment_authorized = Counter(
    "payment_authorized_total",
    "Successful payment authorizations",
)

payment_declined = Counter(
    "payment_declined_total",
    "Declined payment authorizations",
)


def log_event(event, **fields):
    record = {
        "service": ROLE,
        "event": event,
        "timestamp": time.time(),
        **fields,
    }
    print(json.dumps(record), flush=True)


@app.before_request
def before_request():
    request._start_time = time.time()


@app.after_request
def after_request(response):
    elapsed = time.time() - request._start_time

    http_requests.labels(
        ROLE,
        request.path,
        request.method,
        str(response.status_code),
    ).inc()

    http_duration.labels(
        ROLE,
        request.path,
        request.method,
    ).observe(elapsed)

    return response


@app.route("/health")
def health():
    return jsonify({
        "status": "healthy",
        "service": ROLE,
    })


@app.route("/metrics")
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


@app.route("/")
def home():
    return jsonify({
        "service": ROLE,
        "status": "running",
    })


if ROLE == "booking":

    @app.route("/search")
    def search():
        time.sleep(random.uniform(0.05, 0.2))

        log_event(
            "search",
            result_count=5,
        )

        return jsonify({
            "results": 5,
            "status": "success",
        })


    @app.route("/book", methods=["POST"])
    def book():
        booking_attempts.inc()

        customer_email = request.json.get("customer_email", "customer@example.com")
        booking_id = request.json.get(
            "booking_id",
            f"BK-{random.randint(10000, 99999)}",
        )

        forced_delay = request.args.get("delay")

        if forced_delay:
            time.sleep(min(float(forced_delay), 5))

        with tracer.start_as_current_span("booking.create") as span:
            span.set_attribute("booking.id", booking_id)
            span.set_attribute("customer.email_redacted", "***@***")

            try:
                payment_params = {}

                if request.args.get("fail") == "true":
                    payment_params["fail"] = "true"

                payment_response = requests.post(
                    f"{PAYMENT_URL}/pay",
                    params=payment_params,
                    json={
                        "booking_id": booking_id,
                        "amount": 100,
                        "customer_email": customer_email,
                    },
                    timeout=3,
                )

                if payment_response.status_code == 200:
                    booking_success.inc()

                    log_event(
                        "booking_success",
                        booking_id=booking_id,
                        customer_email="***REDACTED***",
                    )

                    return jsonify({
                        "booking_id": booking_id,
                        "payment": "authorized",
                        "status": "booking_confirmed",
                    })

                booking_failure.inc()

                log_event(
                    "booking_failure",
                    booking_id=booking_id,
                    reason="payment_declined",
                )

                return jsonify({
                    "booking_id": booking_id,
                    "payment": "declined",
                    "status": "booking_failed",
                }), 502

            except Exception as exc:
                booking_failure.inc()

                log_event(
                    "booking_failure",
                    booking_id=booking_id,
                    reason=type(exc).__name__,
                )

                return jsonify({
                    "status": "booking_failed",
                    "reason": "payment_service_unavailable",
                }), 503


else:

    @app.route("/pay", methods=["POST"])
    def pay():
        payment_attempts.inc()

        booking_id = request.json.get("booking_id", "unknown")

        if FAIL_PAYMENTS or request.args.get("fail") == "true":
            payment_declined.inc()

            log_event(
                "payment_declined",
                booking_id=booking_id,
                reason="forced_failure",
            )

            return jsonify({
                "authorized": False,
                "status": "declined",
            }), 402

        time.sleep(random.uniform(0.05, 0.15))

        payment_authorized.inc()

        log_event(
            "payment_authorized",
            booking_id=booking_id,
            payment_reference="PAY-REDACTED",
        )

        return jsonify({
            "authorized": True,
            "status": "authorized",
        })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
