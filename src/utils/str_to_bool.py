def str_to_bool(value: str) -> bool:
    if value is None:
        return False
    
    value = value.lower()
    if value in ['true', '1']:
        return True
    elif value in ['false', '0']:
        return False
    else:
        raise ValueError(f"Invalid literal for bool(): {value}")