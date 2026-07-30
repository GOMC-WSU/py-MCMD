def zero_prefix(run_number: int, width: int = 10) -> str:
    """
    Return only the left-pad zeros to make `run_number` occupy `width` digits.
    Example: zero_prefix(123, 6) -> '0000'
    """
    s = str(run_number)
    if len(s) >= width:
        return ""
    return "0" * (width - len(s))


def format_cycle_id(run_number: int, width: int = 10) -> str:
    """
    Return the full zero-padded cycle id string.
    Example: format_cycle_id(123, 6) -> '000123'
    """
    return f"{int(run_number):0{int(width)}d}"