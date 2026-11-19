from datetime import datetime, timedelta, timezone

ARGENTINA_TZ = timezone(timedelta(hours=-3), name="ART")


def ahora_ar() -> datetime:
    """Devuelve la fecha y hora actual en zona horaria de Argentina (UTC-3)."""
    return datetime.now(ARGENTINA_TZ)
