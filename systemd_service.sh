#!/bin/bash
# CCTV Monitor — systemd auto-start configuration
# Run with: sudo bash systemd_service.sh

echo "=========================================="
echo "  CCTV Monitor — systemd Setup"
echo "=========================================="
echo ""

# Must be run as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run with sudo: sudo bash systemd_service.sh"
    exit 1
fi

CURRENT_USER=${SUDO_USER:-$USER}
WORK_DIR=$(pwd)

echo "User:       $CURRENT_USER"
echo "Directory:  $WORK_DIR"
echo ""

# Write the unit file
SERVICE_FILE="/etc/systemd/system/cctv-monitor.service"

cat > $SERVICE_FILE << EOF
[Unit]
Description=CCTV Monitor System
After=graphical.target network.target

[Service]
Type=simple
User=$CURRENT_USER
Environment="DISPLAY=:0"
Environment="XAUTHORITY=/home/$CURRENT_USER/.Xauthority"
WorkingDirectory=$WORK_DIR
ExecStart=/usr/bin/python3 $WORK_DIR/cctv_monitor.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=graphical.target
EOF

# Reload systemd and enable the service
echo "Reloading systemd..."
systemctl daemon-reload

echo "Enabling auto-start..."
systemctl enable cctv-monitor.service

echo ""
echo "=========================================="
echo "  Setup complete!"
echo "=========================================="
echo ""
echo "Service commands:"
echo "  Start:        sudo systemctl start cctv-monitor"
echo "  Stop:         sudo systemctl stop cctv-monitor"
echo "  Status:       sudo systemctl status cctv-monitor"
echo "  Logs:         sudo journalctl -u cctv-monitor -f"
echo "  Disable:      sudo systemctl disable cctv-monitor"
echo ""
