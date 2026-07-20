def to_bool(value)-> bool:
    if value is None:
        return False
    if isinstance(value,bool):
        return value
    if isinstance(value,(bytes,bytearray)):
        return value != b"\x00"
    if isinstance(value, int):
        return value !=0
    
    return bool(value)

def to_int(value)-> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None
    