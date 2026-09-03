"""Optional Web Push adapter; absence never blocks panel notifications."""


class PushUnavailable(RuntimeError):
    """Raised when deployment/browser push support is not configured."""


def send_push(recipient: str, content: str) -> str:
    """Deployment-specific adapter seam; VAPID credentials stay out of source."""
    raise PushUnavailable("browser push is unavailable")
