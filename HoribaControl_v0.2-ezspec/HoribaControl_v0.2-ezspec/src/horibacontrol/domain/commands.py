from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from .models import AcquisitionSettings


class CommandType(str, Enum):
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    INITIALIZE = "initialize"
    MOVE = "move"
    ACQUIRE = "acquire"
    STATUS = "status"
    SELECT_GRATING = "select_grating"
    ABORT = "abort"


@dataclass(frozen=True, slots=True)
class Command:
    type: CommandType
    payload: Any = None
    id: UUID = field(default_factory=uuid4)


def connect_command() -> Command:
    return Command(CommandType.CONNECT)


def disconnect_command() -> Command:
    return Command(CommandType.DISCONNECT)


def initialize_command() -> Command:
    return Command(CommandType.INITIALIZE)


def move_command(wavelength_nm: float) -> Command:
    return Command(CommandType.MOVE, float(wavelength_nm))


def acquire_command(settings: AcquisitionSettings) -> Command:
    return Command(CommandType.ACQUIRE, settings)


def abort_command() -> Command:
    return Command(CommandType.ABORT)


def status_command() -> Command:
    return Command(CommandType.STATUS)


def select_grating_command(grating_number: int) -> Command:
    return Command(CommandType.SELECT_GRATING, int(grating_number))
