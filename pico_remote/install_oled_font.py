"""One-time Thonny-friendly installer for the binary OLED font asset."""

try:
    import ubinascii as binascii
except ImportError:  # Allows a desktop verification run too.
    import binascii


FONT_BASE64 = (
    b"AAAAAAAAAAAAAABPTwAAAAAHBwAABwcAFH9/FBR/fxQAJC5razoSAABjMxgMZmMAADJ/"
    b"TU13clAAAAAEBgMBAAAAHD5jQQAAAABBYz4cAAAIKj4cHD4qCAAICD4+CAgAAACA4GAA"
    b"AAAACAgICAgIAAAAAGBgAAAAAEBgMBgMBgIAPn9JRX8+AABARH9/QEAAAGJzUUlPRgAA"
    b"ImNJSX82AAAYGBQWf38QACdnRUV9OQAAPn9JSXsyAAADA3l9BwMAADZ/SUl/NgAAJm9J"
    b"SX8+AAAAACQkAAAAAACA5GQAAAAACBw2Y0FBAAAUFBQUFBQAAEFBYzYcCAAAAgNRWQ8G"
    b"AAA+f0FNTy4AAHx+Cwt+fAAAf39JSX82AAA+f0FBYyIAAH9/QWM+HAAAf39JSUFBAAB/"
    b"fwkJAQEAAD5/QUl7OgAAf38ICH9/AAAAQX9/QQAAACBgQX8/AQAAf38cNmNBAAB/f0BA"
    b"QEAAAH9/BgwGf38Af38OHH9/AAA+f0FBfz4AAH9/CQkPBgAAHj8hYX9eAAB/fxk5b0YA"
    b"ACZvSUl7MgAAAQF/fwEBAAA/f0BAfz8AAB8/YGA/HwAAf38wGDB/fwBjdxwcd2MAAAcP"
    b"eHgPBwAAYXFZTUdDAAAAf39BQQAAAAIGDBgwYEAAAEFBf38AAAAIDAYGDAgAwMDAwMDA"
    b"wMAAAAEDBgQAAAAgdFRUfHgAAH9/RER8OAAAOHxERGwoAAA4fEREf38AADh8VFRcWAAA"
    b"CH5/CQMCAACYvKSk/HwAAH9/BAR8eAAAAAB9fQAAAABAwICA/X0AAH9/MDhsRAAAAEF/"
    b"f0AAAAB8fBgwGHx8AHx8BAR8eAAAOHxERHw4AAD8/CQkPBgAABg8JCT8/AAAfHwEBAwIA"
    b"ABIXFRUdCAABAQ/f0RkIAAAPHxAQHw8AAAcPGBgPBwAABx8MBgwfBwARGw4OGxEAACcv"
    b"KCg/HwAAERkdFxMRAAACAg+d0FBAAAAAP//AAAAAEFBdz4ICAAAAgMBAwIDAapVqlWqV"
    b"apV"
)

OUTPUT_NAME = "font-pet-me-128.dat"
EXPECTED_LENGTH = 768


def install():
    data = binascii.a2b_base64(FONT_BASE64)
    if len(data) != EXPECTED_LENGTH:
        raise ValueError("font decode length was {}, expected {}".format(
            len(data), EXPECTED_LENGTH
        ))
    with open(OUTPUT_NAME, "wb") as font_file:
        font_file.write(data)
    with open(OUTPUT_NAME, "rb") as font_file:
        written_length = len(font_file.read())
    if written_length != EXPECTED_LENGTH:
        raise OSError("font write verification failed")
    print("Created /{} ({} bytes)".format(OUTPUT_NAME, written_length))
    print("You may now delete install_oled_font.py from the Pico.")


if __name__ == "__main__":
    install()

