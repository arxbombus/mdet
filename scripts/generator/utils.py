from typing import Optional, NotRequired, TypedDict, TypeVar

T = TypeVar("T", bound=TypedDict("T", {}))
U = TypeVar("U", bound=TypedDict("U", {}))


def resolve_config(config: T, default_config: U):
    _config = default_config.copy()
    if config:
        for key in _config:
            if key in config:
                _config[key] = config[key]
    return _config
