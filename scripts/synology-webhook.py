#!/usr/bin/env python3
"""
Synology NAS Webhook Deployment Server
Receives GitHub webhook and triggers deployment on Synology NAS
"""

import os
import json
import hmac
import hashlib
import subprocess
from flask import Flask, request, jsonify
import logging
from datetime import datetime

app = Flask(__name__)

# Configuration
NAS_HOST = "192.168.50.215"
NAS_PORT = "1111"
NAS_USER = "qws941"
NAS_BASE_DIR = "/volume1/docker/blacklist"
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "your-webhook-secret")
REGISTRY_IMAGE = "registry.jclee.me/blacklist:latest"

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("/var/log/synology-webhook.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def verify_webhook_signature(payload, signature):
    """Verify GitHub webhook signature"""
    if not signature:
        return False

    sha_name, signature_hash = signature.split("=")
    if sha_name != "sha256":
        return False

    mac = hmac.new(WEBHOOK_SECRET.encode(), msg=payload, digestmod=hashlib.sha256)
    return hmac.compare_digest(mac.hexdigest(), signature_hash)


def deploy_to_nas():
    """Execute deployment to Synology NAS"""
    try:
        # SSH command to update on NAS
        ssh_command = [
            "ssh",
            "-p",
            NAS_PORT,
            f"{NAS_USER}@{NAS_HOST}",
            f"cd {NAS_BASE_DIR} && docker-compose pull && docker-compose down && docker-compose up -d",
        ]

        result = subprocess.run(
            ssh_command, capture_output=True, text=True, timeout=120
        )

        if result.returncode == 0:
            logger.info("Deployment successful")
            return True, result.stdout
        else:
            logger.error(f"Deployment failed: {result.stderr}")
            return False, result.stderr

    except subprocess.TimeoutExpired:
        logger.error("Deployment timeout")
        return False, "Deployment timeout"
    except Exception as e:
        logger.error(f"Deployment error: {e}")
        return False, str(e)


@app.route("/webhook", methods=["POST"])
def github_webhook():
    """Handle GitHub webhook"""
    # Verify signature
    signature = request.headers.get("X-Hub-Signature-256")
    if not verify_webhook_signature(request.data, signature):
        logger.warning("Invalid webhook signature")
        return jsonify({"error": "Invalid signature"}), 401

    # Parse payload
    payload = request.json

    # Check if it's a push to main branch
    if payload.get("ref") != "refs/heads/main":
        return jsonify({"message": "Not main branch, skipping"}), 200

    # Log deployment request
    logger.info(
        f"Deployment triggered by {payload.get('pusher', {}).get('name', 'unknown')}"
    )

    # Execute deployment
    success, output = deploy_to_nas()

    if success:
        return (
            jsonify(
                {
                    "status": "success",
                    "message": "Deployment completed",
                    "timestamp": datetime.now().isoformat(),
                }
            ),
            200,
        )
    else:
        return (
            jsonify(
                {
                    "status": "failed",
                    "message": "Deployment failed",
                    "error": output,
                    "timestamp": datetime.now().isoformat(),
                }
            ),
            500,
        )


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200


@app.route("/deploy", methods=["POST"])
def manual_deploy():
    """Manual deployment trigger"""
    # Check for API key
    api_key = request.headers.get("X-API-Key")
    if api_key != os.environ.get("DEPLOY_API_KEY"):
        return jsonify({"error": "Unauthorized"}), 401

    logger.info("Manual deployment triggered")
    success, output = deploy_to_nas()

    if success:
        return (
            jsonify(
                {
                    "status": "success",
                    "message": "Manual deployment completed",
                    "output": output,
                }
            ),
            200,
        )
    else:
        return (
            jsonify(
                {
                    "status": "failed",
                    "message": "Manual deployment failed",
                    "error": output,
                }
            ),
            500,
        )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
