import os


class DatabaseConfigurationError(RuntimeError):
    pass


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise DatabaseConfigurationError(
            "DATABASE_URL no está configurada. Configurá la URL de PostgreSQL "
            "en el archivo .env."
        )
    return database_url
