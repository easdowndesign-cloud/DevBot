"""Command-line monitor for the DevBot Pico remote receiver."""

from __future__ import annotations

import queue

from receiver_core import RadioReceiver, ReceiverEvent


def main() -> int:
    events: "queue.Queue[ReceiverEvent]" = queue.Queue(maxsize=100)
    receiver = RadioReceiver(events)
    receiver.start()
    last_direction = None
    print("DevBot Pi 4 receiver starting")
    try:
        while True:
            event = events.get()
            if event.kind == "status":
                print("RADIO {}".format(event.detail))
            elif event.kind == "error":
                print("RADIO ERROR {}".format(event.detail))
            elif event.telemetry is not None:
                data = event.telemetry
                if data.direction != last_direction:
                    print(
                        "RX seq={} X={} Y={} direction={} RSSI={}dBm".format(
                            data.sequence,
                            data.raw_x,
                            data.raw_y,
                            data.direction,
                            data.rssi,
                        )
                    )
                    last_direction = data.direction
    except KeyboardInterrupt:
        print("\nReceiver stopped")
    finally:
        receiver.stop()
        receiver.join(timeout=1.0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
