"""TCP/RS485 protocol for AdvanSol DCON-WIFI / MRO/MR optimizers."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
import logging

_LOGGER = logging.getLogger(__name__)


class AdvansolError(Exception):
    """Base exception for AdvanSol protocol errors."""


class AdvansolResponseError(AdvansolError):
    """Raised when a device response cannot be parsed."""


@dataclass(slots=True)
class OptimizerModule:
    """An optimizer module discovered on the controller."""

    index: int
    serial_number: str


@dataclass(slots=True)
class ModuleData:
    """Decoded optimizer module values."""

    index: int
    serial_number: str
    mos: int
    switch_on: bool
    software: str
    hardware: str
    output_voltage: float
    output_current: float
    temperature: float
    power: int
    energy: float
    input_voltage: float
    input_current: float
    raw: str
    last_update: datetime


def _crc16(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc & 0xFFFF


def _make_frame(payload: bytes) -> bytes:
    frame = bytearray([0xFF] * 256)
    frame[: len(payload)] = payload
    crc = _crc16(bytes(frame[:254]))
    frame[254] = crc & 0xFF
    frame[255] = (crc >> 8) & 0xFF
    return bytes(frame)


def _hex(data: bytes) -> str:
    return data.hex().upper()


def _u16(data: bytes, pos: int) -> int:
    return int.from_bytes(data[pos : pos + 2], "big", signed=False)


def _i16(data: bytes, pos: int) -> int:
    return int.from_bytes(data[pos : pos + 2], "big", signed=True)


def _u32(data: bytes, pos: int) -> int:
    return int.from_bytes(data[pos : pos + 4], "big", signed=False)


class AdvansolClient:
    """Async client for the AdvanSol TCP RS485 bridge."""

    def __init__(
        self,
        host: str,
        tcp_port: int,
        request_timeout: float,
        switch_retries: int,
        switch_retry_delay: float,
    ) -> None:
        self.host = host
        self.tcp_port = tcp_port
        self.request_timeout = request_timeout
        self.switch_retries = switch_retries
        self.switch_retry_delay = switch_retry_delay
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._lock = asyncio.Lock()

    @property
    def connected(self) -> bool:
        """Return true if a TCP connection exists."""
        return self._writer is not None and not self._writer.is_closing()

    async def connect(self) -> None:
        """Connect to the bridge."""
        if self.connected:
            return
        await self.close()
        self._reader, self._writer = await asyncio.wait_for(
            asyncio.open_connection(self.host, self.tcp_port),
            timeout=self.request_timeout,
        )
        _LOGGER.info("Connected to AdvanSol bridge %s:%s", self.host, self.tcp_port)

    async def close(self) -> None:
        """Close the TCP connection."""
        if self._writer is not None:
            self._writer.close()
            try:
                await self._writer.wait_closed()
            except (ConnectionError, RuntimeError):
                pass
        self._reader = None
        self._writer = None

    async def _ensure_connected(self) -> None:
        if not self.connected:
            await self.connect()

    async def request(self, payload: bytes, timeout: float | None = None) -> bytes:
        """Send a request frame and return the raw response."""
        async with self._lock:
            await self._ensure_connected()
            assert self._reader is not None
            assert self._writer is not None

            self._writer.write(_make_frame(payload))
            await self._writer.drain()

            chunks: list[bytes] = []
            deadline = timeout if timeout is not None else self.request_timeout
            loop = asyncio.get_running_loop()
            end = loop.time() + deadline

            while True:
                remaining = end - loop.time()
                if remaining <= 0:
                    break
                try:
                    chunk = await asyncio.wait_for(self._reader.read(256), timeout=remaining)
                except asyncio.TimeoutError:
                    break
                if not chunk:
                    await self.close()
                    raise AdvansolError("TCP connection closed")
                chunks.append(chunk)
                if sum(len(item) for item in chunks) >= 256:
                    break
                try:
                    chunk = await asyncio.wait_for(self._reader.read(256), timeout=0.35)
                except asyncio.TimeoutError:
                    break
                if chunk:
                    chunks.append(chunk)
                    if sum(len(item) for item in chunks) >= 256:
                        break

            return b"".join(chunks)

    async def read_controller_serial(self) -> str:
        """Read the controller serial number."""
        response = await self.request(bytes([0x00, 0x03, 0xFF, 0xE7, 0x00, 0x03]))
        if len(response) >= 9 and response[0] == 0x01 and response[1] == 0x03 and response[2] == 0x06:
            return _hex(response[3:9])
        raise AdvansolResponseError(f"Invalid controller serial response: {_hex(response)}")

    async def read_device_list(self, controller_serial: str) -> list[OptimizerModule]:
        """Read optimizer module list from the controller."""
        serial_bytes = bytes.fromhex(controller_serial)
        response = await self.request(bytes([0x00, 0x42, 0x01, *serial_bytes]), timeout=2.5)

        if not (len(response) > 20 and response[0] == 0x01 and response[1] == 0x42):
            raise AdvansolResponseError(f"Invalid device list response: {_hex(response)}")

        count = _u16(response, 6)
        modules: list[OptimizerModule] = []
        for idx in range(count):
            pos = 10 + idx * 10
            if pos + 6 > len(response):
                break
            serial = _hex(response[pos : pos + 6])
            if serial != "FFFFFFFFFFFF" and len(serial) == 12:
                modules.append(OptimizerModule(index=idx + 1, serial_number=serial))
        return modules

    async def read_module(self, index: int) -> ModuleData:
        """Read one optimizer module."""
        response = await self.request(bytes([0x00, 0x43, 0x00, index, 0x00, 0x17]), timeout=2.5)
        return parse_module_response(index, response)

    async def switch_module(self, serial_number: str, target_on: bool) -> None:
        """Switch optimizer MOS on or off."""
        serial_bytes = bytes.fromhex(serial_number)
        if len(serial_bytes) != 6:
            raise AdvansolError(f"Invalid serial number: {serial_number}")

        state_bytes = [0xFF, 0x00] if target_on else [0x00, 0x00]
        payload = bytes([0x00, 0x05, 0xFF, 0xEF, *state_bytes, *serial_bytes])

        for attempt in range(1, self.switch_retries + 1):
            try:
                response = await self.request(payload, timeout=1.2)
                _LOGGER.debug(
                    "Switch command %s -> %s try %s/%s response %s",
                    serial_number,
                    target_on,
                    attempt,
                    self.switch_retries,
                    _hex(response),
                )
            except AdvansolError as err:
                _LOGGER.warning(
                    "Switch command %s -> %s try %s/%s failed: %s",
                    serial_number,
                    target_on,
                    attempt,
                    self.switch_retries,
                    err,
                )
            if attempt < self.switch_retries:
                await asyncio.sleep(self.switch_retry_delay)


def parse_module_response(index: int, response: bytes) -> ModuleData:
    """Decode a module response."""
    if not (len(response) > 40 and response[0] == 0x01 and response[1] == 0x43):
        raise AdvansolResponseError(f"Module {index}: invalid response: {_hex(response)}")

    serial = _hex(response[3:9])
    mos = _u16(response, 9)
    software = ".".join(f"{byte:02X}" for byte in response[11:15])
    hardware = ".".join(f"{byte:02X}" for byte in response[15:19])

    return ModuleData(
        index=index,
        serial_number=serial,
        mos=mos,
        switch_on=mos == 1,
        software=software,
        hardware=hardware,
        output_voltage=_i16(response, 19) / 100,
        output_current=_i16(response, 21) / 100,
        temperature=_u16(response, 23) - 100,
        power=_i16(response, 25),
        energy=_u32(response, 27) / 100,
        input_voltage=_i16(response, 31) / 100,
        input_current=_i16(response, 33) / 100,
        raw=_hex(response),
        last_update=datetime.now().astimezone(),
    )
