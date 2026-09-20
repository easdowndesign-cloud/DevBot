#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
UNIT_NAME="devbot-web.service"
UNIT_TEMPLATE="$APP_DIR/$UNIT_NAME"
UNIT_TARGET="/etc/systemd/system/$UNIT_NAME"
APP_USER="${SUDO_USER:-service}"
APP_HOME="$(getent passwd "$APP_USER" | cut -d: -f6)"

if [[ "$EUID" -ne 0 ]]; then
    echo "Run this installer with sudo."
    echo "Example: sudo ./install_web_app.sh --install"
    exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3 is not installed."
    exit 1
fi

if ! python3 -c "import serial, smbus2" >/dev/null 2>&1; then
    echo "Missing native Python hardware packages."
    echo "Run: sudo apt install -y python3-serial python3-smbus2"
    exit 1
fi

if [[ ! -f "$APP_DIR/web/index.html" ]]; then
    echo "Missing $APP_DIR/web/index.html"
    exit 1
fi

install_service() {
    if pgrep -u "$APP_USER" -f -- "$APP_DIR/dashboard.py" >/dev/null 2>&1; then
        echo "Close the graphical DevBot dashboard before installing the web service."
        exit 1
    fi

    chmod 0755 "$APP_DIR/run_web_dashboard.sh"
    sed \
        -e "s|@APP_DIR@|$APP_DIR|g" \
        -e "s|@APP_USER@|$APP_USER|g" \
        "$UNIT_TEMPLATE" > "$UNIT_TARGET"
    chmod 0644 "$UNIT_TARGET"

    # Prevent the desktop dashboard from competing for the radio after login.
    rm -f "$APP_HOME/.config/autostart/devbot-receiver.desktop"

    systemctl daemon-reload
    systemctl enable --now "$UNIT_NAME"
    echo "DevBot web dashboard installed and started."
    echo "Open: http://devbot.local:8080"
}

case "${1:---install}" in
    --install)
        install_service
        ;;
    --restart)
        systemctl restart "$UNIT_NAME"
        echo "DevBot web dashboard restarted."
        ;;
    --status)
        systemctl status "$UNIT_NAME" --no-pager
        ;;
    --uninstall)
        systemctl disable --now "$UNIT_NAME" >/dev/null 2>&1 || true
        rm -f "$UNIT_TARGET"
        systemctl daemon-reload
        echo "DevBot web dashboard service removed."
        echo "The program files were not deleted."
        ;;
    *)
        echo "Usage: sudo ./install_web_app.sh [--install|--restart|--status|--uninstall]"
        exit 2
        ;;
esac
