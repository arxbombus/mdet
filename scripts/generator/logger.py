from typing import NotRequired, TypedDict
import logging
from scripts.generator.utils import resolve_config


class LoggerConfig(TypedDict):
    name: NotRequired[str]
    is_enabled: NotRequired[bool]
    level: NotRequired[int]
    format: NotRequired[str]


class LoggerConfigRequired(TypedDict):
    name: str
    is_enabled: bool
    level: int
    format: str


DEFAULT_LOGGER_CONFIG: LoggerConfigRequired = {
    "name": "logger",
    "is_enabled": True,
    "level": logging.DEBUG,
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
}


class Logger:
    def __init__(self, config: LoggerConfig | None = None):
        self.config = resolve_config(config or {}, DEFAULT_LOGGER_CONFIG)
        self.logger = logging.getLogger(self.config["name"])
        self.set_configuration()

    def set_configuration(self):
        if not self.config["is_enabled"]:
            self.logger.disabled = True
            return

        self.logger.setLevel(self.config["level"])
        self.formatter = logging.Formatter(self.config["format"])
        self.ch = logging.StreamHandler()
        self.ch.setFormatter(self.formatter)
        self.logger.addHandler(self.ch)
