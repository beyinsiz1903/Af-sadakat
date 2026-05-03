"""Optional Sentry initialization. No-op if SENTRY_DSN is not set."""
import os
import logging

logger = logging.getLogger("omnihub.sentry")


def init_sentry() -> bool:
    dsn = os.environ.get("SENTRY_DSN", "").strip()
    if not dsn:
        logger.info("Sentry: SENTRY_DSN not set, skipping init (no-op)")
        return False
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration

        env = os.environ.get("SENTRY_ENV", os.environ.get("APP_ENV", "development"))
        traces_sample_rate = float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.1"))

        sentry_sdk.init(
            dsn=dsn,
            environment=env,
            traces_sample_rate=traces_sample_rate,
            send_default_pii=False,
            integrations=[
                FastApiIntegration(),
                StarletteIntegration(),
                LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
            ],
        )
        logger.info("Sentry initialized (env=%s, sample=%.2f)", env, traces_sample_rate)
        return True
    except ImportError:
        logger.warning("Sentry: sentry-sdk not installed, skipping")
        return False
    except Exception as e:
        logger.error("Sentry init failed: %s", e)
        return False
