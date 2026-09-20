# DevBot remote-to-robot protocol v1

This is the handoff contract for the future Raspberry Pi 4 receiver. The Pico
implementation is authoritative in `protocol.py`.

## Transport settings

| Setting | Remote | Robot |
|---|---:|---:|
| Radio group | 73 | 73 |
| Radio address | 1 | 2 |
| Speed | 2 | 2 |
| Frequency | 922 MHz | 922 MHz |
| Transmit power | 20 | Project decision |
| Pair ID | `0x44425631` | `0x44425631` |

The pair ID is accidental cross-talk protection, not encryption or
authentication.

All multibyte fields use network byte order (big-endian). CRC is
CRC-16-CCITT-FALSE: polynomial `0x1021`, initial value `0xFFFF`, no reflection,
no final XOR. The check vector `123456789` produces `0x29B1`.

## Control frame: 24 bytes

Python format: `>2sBBIHHIhhHH`

| Offset | Size | Field | Meaning |
|---:|---:|---|---|
| 0 | 2 | magic | ASCII `DB` |
| 2 | 1 | version | `1` |
| 3 | 1 | type | `0x01` control |
| 4 | 4 | pair ID | `0x44425631` |
| 8 | 2 | session ID | New non-zero value per remote boot |
| 10 | 2 | sequence | Unsigned, increments modulo 65536 |
| 12 | 4 | uptime ms | Remote monotonic uptime modulo 2^32 |
| 16 | 2 | steer | Signed `-1000..1000` |
| 18 | 2 | throttle | Signed `-1000..1000` |
| 20 | 2 | flags | Bit mask below |
| 22 | 2 | CRC | CRC over bytes 0..21 |

Control flags:

- bit 0: active
- bit 1: neutral/centred interlock completed
- bit 2: remote fault
- bit 3: display degraded
- bit 4: link recovery/re-arm required

The robot must reject a frame when active bit 0 is clear but either axis is
non-zero. It should also apply its own receive timeout and immediately disable
motor drive when valid control frames stop.

## Acknowledgement frame: 22 bytes

Python format: `>2sBBIHHBBHIH`

| Offset | Size | Field | Meaning |
|---:|---:|---|---|
| 0 | 2 | magic | ASCII `DB` |
| 2 | 1 | version | `1` |
| 3 | 1 | type | `0x02` acknowledgement |
| 4 | 4 | pair ID | Must match control frame |
| 8 | 2 | session ID | Echo current remote session |
| 10 | 2 | ack sequence | Sequence of accepted control frame |
| 12 | 1 | robot state | `0..8` |
| 13 | 1 | bumper mask | bits 0..2, one per bumper |
| 14 | 2 | robot fault flags | Defined by receiver; v1 permits bits 0..4 |
| 16 | 4 | robot uptime ms | Robot monotonic uptime modulo 2^32 |
| 20 | 2 | CRC | CRC over bytes 0..19 |

Robot states are 0 boot, 1 disabled, 2 ready, 3 forward, 4 reverse, 5 turn
left, 6 turn right, 7 obstacle, and 8 fault.

## Receiver obligations

1. Validate exact length, CRC, magic, version, type, pair ID and field ranges
   before acting on any frame.
2. Track session ID. A changed session begins a new sequence space and must not
   bypass the robot's own safe-enable policy.
3. Ignore duplicate/out-of-order control sequences using modulo-65536 ordering.
4. Apply an independent control timeout and disable the motor driver on stale
   data, parser failure, bumper activation, or process failure.
5. Echo only a control sequence the robot actually accepted.
6. Send acknowledgements often enough that the remote receives one within 500
   ms. A cadence at or below the 20 ms control period is preferred.
7. Never treat the handheld remote as the sole safety layer; bumpers and motor
   disable logic belong at the robot endpoint.
