"""Constants for the AdvanSol Optimizer integration."""

from __future__ import annotations

DOMAIN = "advansol_optimizer"

CONF_TCP_PORT = "tcp_port"
CONF_POLL_INTERVAL = "poll_interval"
CONF_REQUEST_TIMEOUT = "request_timeout"
CONF_SWITCH_RETRIES = "switch_retries"
CONF_SWITCH_RETRY_DELAY = "switch_retry_delay"
CONF_NIGHT_START = "night_start"
CONF_NIGHT_END = "night_end"

DEFAULT_HOST = "192.168.2.156"
DEFAULT_TCP_PORT = 502
DEFAULT_POLL_INTERVAL = 10
DEFAULT_REQUEST_TIMEOUT = 5
DEFAULT_SWITCH_RETRIES = 3
DEFAULT_SWITCH_RETRY_DELAY = 4.1
DEFAULT_NIGHT_START = 22
DEFAULT_NIGHT_END = 5

PLATFORMS = ["sensor", "binary_sensor", "switch"]
