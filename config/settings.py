"""
AIOps Sentinel — Central Configuration
Loads all settings from environment variables with safe defaults.
"""

import os
from dotenv import load_dotenv

# Load .env file (only active in local dev; ignored in Lambda)
load_dotenv()


class Settings:
    # AWS
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    AWS_ACCOUNT_ID: str = os.getenv("AWS_ACCOUNT_ID", "")

    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "dev")

    # Groq AI
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MAX_TOKENS: int = int(os.getenv("GROQ_MAX_TOKENS", "2048"))

    # SNS
    SNS_TOPIC_ARN: str = os.getenv("SNS_TOPIC_ARN", "")

    # DynamoDB
    DYNAMODB_TABLE_NAME: str = os.getenv("DYNAMODB_TABLE_NAME", "aiops-incidents")

    # Slack
    SLACK_WEBHOOK_URL: str = os.getenv("SLACK_WEBHOOK_URL", "")
    SLACK_CHANNEL: str = os.getenv("SLACK_CHANNEL", "#aiops-alerts")
    SECRETS_MANAGER_SLACK_SECRET_NAME: str = os.getenv(
        "SECRETS_MANAGER_SLACK_SECRET_NAME", "aiops/slack/webhook"
    )

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Lambda
    LAMBDA_TIMEOUT: int = int(os.getenv("LAMBDA_TIMEOUT", "300"))
    LAMBDA_MEMORY: int = int(os.getenv("LAMBDA_MEMORY", "512"))

    # S3
    S3_LOG_ARCHIVE_BUCKET: str = os.getenv("S3_LOG_ARCHIVE_BUCKET", "")

    # Alarm thresholds
    CPU_ALARM_THRESHOLD: float = float(os.getenv("CPU_ALARM_THRESHOLD", "80"))
    MEMORY_ALARM_THRESHOLD: float = float(os.getenv("MEMORY_ALARM_THRESHOLD", "85"))
    ERROR_RATE_THRESHOLD: float = float(os.getenv("ERROR_RATE_THRESHOLD", "5"))

    @classmethod
    def is_production(cls) -> bool:
        return cls.ENVIRONMENT == "prod"

    @classmethod
    def is_local(cls) -> bool:
        return cls.ENVIRONMENT == "dev"


settings = Settings()
