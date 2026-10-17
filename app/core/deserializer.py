import json
from typing import Any


def deserializar_json_string(data: Any) -> Any:
    """Deserializa datos que pueden ser dict, bytes, str o str doblemente serializado desde Bonita."""
    if isinstance(data, (bytes, bytearray)):
        data = data.decode("utf-8")
    if isinstance(data, str):
        data = data.strip()
        if not data:
            return {}
        try:
            parsed = json.loads(data)
            # Manejo de string JSON doblemente serializado (ej: '"{\\"id\\": 1}"')
            if isinstance(parsed, str):
                parsed = json.loads(parsed)
            return parsed
        except Exception:
            # Si no es parseable como json directo, retorna el dato para que pydantic reporte error adecuado
            return data
    return data
