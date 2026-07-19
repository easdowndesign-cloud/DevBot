from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path

from devbot_pi.app import DevBotSupervisor
from devbot_pi.comms.arduino_serial import SerialArduinoLink
from devbot_pi.config import AppConfig
from devbot_pi.hardware.mock import MockArduinoLink


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the DevBot Raspberry Pi supervisor")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--mock", action="store_true", help="Use an in-memory Arduino adapter")
    parser.add_argument("--run-seconds", type=float, help="Stop after a test interval")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    config = AppConfig.from_toml(args.config) if args.config else AppConfig()
    link = (
        MockArduinoLink()
        if args.mock
        else SerialArduinoLink(config.serial_port, config.serial_baudrate)
    )
    asyncio.run(DevBotSupervisor(config, link).run(args.run_seconds))


if __name__ == "__main__":
    main()

