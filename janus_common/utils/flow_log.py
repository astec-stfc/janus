import logging
import os
import sys
from configparser import ConfigParser
from typing import Iterable


BOOLEAN_STATES = ConfigParser.BOOLEAN_STATES
LOGGER_NAME = "janus.flow"

PHASE_WIDTH = 22
LOCAL_STEP_WIDTH = 4
CLIENT_VALUE_WIDTH = 10
CLIENT_FIELD_WIDTH = len("client=") + CLIENT_VALUE_WIDTH
REQUEST_VALUE_WIDTH = 8
REQUEST_FIELD_WIDTH = len("req=") + REQUEST_VALUE_WIDTH

PHASE_SUMMARIES = {
    "G01 epics.change": "client detects PV change",
    "G02 api.accept": "lattice-api accepts PATCH and stores request",
    "G03 restframe.submit": "comm-to-restframe submits request to RestFrame",
    "G04 tracking.publish": "RestFrame publishes tracking_started",
    "G05 tracking.observe": "client consumes tracking_started and sets SIMULATION:STATUS=1",
    "G06 tracking.done": "RestFrame finishes tracking",
    "G07 results.store": "comm-to-restframe stores completed result in lattice-api",
    "G08 results.stored": "lattice-api stores result and publishes lattice_added",
    "G09 results.apply": "client consumes result and sets SIMULATION:STATUS=0",
}


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default

    normalised = value.strip().lower()
    if normalised not in BOOLEAN_STATES:
        raise ValueError(
            f"{name} must be one of: 1, yes, true, on, 0, no, false, off"
        )

    return BOOLEAN_STATES[normalised]


def is_flow_log_verbose() -> bool:
    return env_bool("FLOW_LOG_VERBOSE", default=False)


def truncate(value: object, max_length: int) -> str:
    if value is None or value == "":
        return "-"

    value = str(value)
    if len(value) <= max_length:
        return value
    return value[: max_length - 3] + "..."


def short_id(value: str | None, length: int = REQUEST_VALUE_WIDTH) -> str:
    if not value:
        return "pending"
    return str(value)[:length]


def centred(value: object, width: int) -> str:
    return f"{truncate(value, width):^{width}}"


class FlowFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        phase = getattr(record, "flow_phase")
        local_step = getattr(record, "flow_local_step")
        client_id = getattr(record, "flow_client_id", None)
        request_id = getattr(record, "flow_request_id", None)
        current = getattr(record, "flow_current", None)
        next_step = getattr(record, "flow_next_step", None)
        fields = getattr(record, "flow_fields", ())

        summary = PHASE_SUMMARIES.get(phase, current or "-")
        client_field = f"client={truncate(client_id, CLIENT_VALUE_WIDTH)}"
        request_field = f"req={short_id(request_id)}"

        lines = [
            (
                f"[{centred(phase, PHASE_WIDTH)} | "
                f"{centred(local_step, LOCAL_STEP_WIDTH)} | "
                f"{centred(client_field, CLIENT_FIELD_WIDTH)} | "
                f"{centred(request_field, REQUEST_FIELD_WIDTH)} | "
                f"{summary}]"
            )
        ]

        if is_flow_log_verbose():
            if current:
                lines.append(f"    current: {current}")
            if request_id:
                lines.append(f"    request_id: {request_id}")
            for label, value in fields:
                if value is not None:
                    lines.append(f"    {label}: {value}")
            if next_step:
                lines.append(f"       next: {next_step}")

        return "\n".join(lines)


def get_flow_logger() -> logging.Logger: # get singleton logger
    logger = logging.getLogger(LOGGER_NAME)
    # checks if handler already attached to prevent duplicate handler
    if not any(getattr(handler, "flow_handler", False) for handler in logger.handlers): 
        handler = logging.StreamHandler(sys.stdout)
        handler.flow_handler = True
        handler.setFormatter(FlowFormatter())
        logger.addHandler(handler)
        logger.propagate = False
    logger.setLevel(logging.INFO)
    return logger


def flow_log(
    phase: str,
    local_step: str,
    *,
    client_id: str | None = None,
    request_id: str | None = None,
    current: str | None = None,
    next_step: str | None = None,
    fields: Iterable[tuple[str, object]] | None = None,
) -> None:
    get_flow_logger().info(
        "",
        extra={
            "flow_event": True,
            "flow_phase": phase,
            "flow_local_step": local_step,
            "flow_client_id": client_id,
            "flow_request_id": request_id,
            "flow_current": current,
            "flow_next_step": next_step,
            "flow_fields": tuple(fields or ()),
        },
    )
