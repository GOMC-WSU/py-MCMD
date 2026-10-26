"""Read named JSON sections while preserving the existing setting names."""

CONFIG_SECTIONS = frozenset(
    {
        "simulation",
        "gcmc",
        "run_control",
        "execution",
        "engines",
        "force_fields",
        "box_0",
        "box_1",
        "output",
    }
)


def flatten_config_sections(data: dict) -> dict:
    """Accept flat or sectioned input and reject ambiguous duplicate settings."""
    if not isinstance(data, dict):
        raise ValueError("Simulation configuration must be a JSON object")
    flattened = {}
    sources = {}
    for name, value in data.items():
        if name in CONFIG_SECTIONS:
            if not isinstance(value, dict):
                raise ValueError(
                    f"Configuration section '{name}' must be a JSON object"
                )
            entries = value.items()
            source = name
        else:
            entries = [(name, value)]
            source = "top level"
        for key, setting in entries:
            if key in CONFIG_SECTIONS:
                raise ValueError(
                    f"Configuration section '{key}' cannot be nested inside '{name}'"
                )
            if key in flattened:
                raise ValueError(
                    f"Setting '{key}' appears in both '{sources[key]}' and '{source}'"
                )
            flattened[key] = setting
            sources[key] = source
    return flattened
