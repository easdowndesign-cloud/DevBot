#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
MENU_DIR="$HOME/.local/share/applications"
AUTOSTART_DIR="$HOME/.config/autostart"
DESKTOP_DIR="$HOME/Desktop"
MENU_FILE="$MENU_DIR/devbot-receiver.desktop"
AUTOSTART_FILE="$AUTOSTART_DIR/devbot-receiver.desktop"
DESKTOP_FILE="$DESKTOP_DIR/DevBot Receiver.desktop"
OLD_UNIT="$HOME/.config/systemd/user/devbot-receiver.service"

if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3 is not installed."
    exit 1
fi

if ! python3 -c "import tkinter" >/dev/null 2>&1; then
    echo "Tkinter is not installed. Run: sudo apt install -y python3-tk"
    exit 1
fi

if ! python3 -c "import serial, smbus2" >/dev/null 2>&1; then
    echo "Missing native Python hardware packages."
    echo "Run: sudo apt install -y python3-serial python3-smbus2"
    exit 1
fi

install_files() {
    mkdir -p "$MENU_DIR" "$AUTOSTART_DIR" "$DESKTOP_DIR"
    chmod 0755 "$APP_DIR/run_dashboard.sh"
    sed "s|@APP_DIR@|$APP_DIR|g" "$APP_DIR/devbot-receiver.desktop" > "$MENU_FILE"
    chmod 0755 "$MENU_FILE"
    cp "$MENU_FILE" "$DESKTOP_FILE"
    chmod 0755 "$DESKTOP_FILE"

    # Remove the previous headless service so it cannot compete for the radio.
    systemctl --user disable --now devbot-receiver.service >/dev/null 2>&1 || true
    rm -f "$OLD_UNIT"
    systemctl --user daemon-reload

    if command -v gio >/dev/null 2>&1; then
        gio set "$DESKTOP_FILE" metadata::trusted true >/dev/null 2>&1 || true
    fi
}

case "${1:---install}" in
    --install)
        install_files
        echo "DevBot Receiver dashboard icon installed."
        echo "Autostart remains unchanged."
        ;;
    --enable-autostart)
        install_files
        cp "$MENU_FILE" "$AUTOSTART_FILE"
        chmod 0644 "$AUTOSTART_FILE"
        echo "DevBot Receiver graphical autostart is ENABLED."
        echo "It will open at the next desktop login."
        ;;
    --disable-autostart)
        rm -f "$AUTOSTART_FILE"
        echo "DevBot Receiver graphical autostart is DISABLED."
        echo "A dashboard already open is not closed by this command."
        ;;
    --status)
        if [[ -f "$AUTOSTART_FILE" ]]; then
            echo "Autostart: enabled"
        else
            echo "Autostart: disabled"
        fi
        if pgrep -f -- "$APP_DIR/dashboard.py" >/dev/null 2>&1; then
            echo "Dashboard: running"
        else
            echo "Dashboard: stopped"
        fi
        ;;
    *)
        echo "Usage: $0 [--install|--enable-autostart|--disable-autostart|--status]"
        exit 2
        ;;
esac
