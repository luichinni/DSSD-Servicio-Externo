from getpass import getpass

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.security import hash_password
from app.db.session import get_session_factory
from app.models.user import User


def main() -> None:
    try:
        email = str(TypeAdapter(EmailStr).validate_python(input("Email: "))).lower()
    except ValidationError as exc:
        raise SystemExit("Email inválido.") from exc

    password = getpass("Contraseña: ")
    confirmation = getpass("Confirmar contraseña: ")
    if len(password) < 12:
        raise SystemExit("La contraseña debe tener al menos 12 caracteres.")
    if password != confirmation:
        raise SystemExit("Las contraseñas no coinciden.")

    with get_session_factory()() as db:
        if db.scalar(select(User.id).where(User.email == email)) is not None:
            raise SystemExit("Ya existe un usuario con ese email.")

        db.add(User(email=email, hashed_password=hash_password(password)))
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise SystemExit("No se pudo crear el usuario; verificá si ya existe.") from exc

    print("Usuario creado.")


if __name__ == "__main__":
    main()
