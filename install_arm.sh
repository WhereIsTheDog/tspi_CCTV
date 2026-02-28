#!/bin/bash
# CCTV Monitor — ARM Debian/Ubuntu installation script
# Run with: sudo bash install_arm.sh

echo "=========================================="
echo "  CCTV Monitor — ARM Installer"
echo "=========================================="
echo ""

# Must be run as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run with sudo: sudo bash install_arm.sh"
    exit 1
fi

# Update package index
echo "[1/6] Updating package index..."
apt-get update

# Install system dependencies
echo "[2/6] Installing system dependencies..."
apt-get install -y \
    python3 \
    python3-pip \
    python3-tk \
    python3-dev \
    libopencv-dev \
    libatlas-base-dev \
    libjpeg-dev \
    libtiff-dev \
    libpng-dev \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    libxvidcore-dev \
    libx264-dev \
    libgtk-3-dev \
    libcanberra-gtk-module \
    libcanberra-gtk3-module \
    ffmpeg

# Upgrade pip
echo "[3/6] Upgrading pip..."
python3 -m pip install --upgrade pip

# Install Python dependencies
echo "[4/6] Installing Python packages..."
pip3 install -r requirements_arm.txt

# Create desktop shortcut
echo "[5/6] Creating desktop shortcut..."
DESKTOP_FILE="/usr/share/applications/cctv-monitor.desktop"
cat > $DESKTOP_FILE << EOF
[Desktop Entry]
Name=CCTV Monitor
Comment=Full-screen CCTV preview system
Exec=python3 $(pwd)/cctv_monitor.py
Icon=video-display
Terminal=false
Type=Application
Categories=AudioVideo;Video;
EOF
chmod +x $DESKTOP_FILE

# Create run script
echo "[6/6] Creating run script..."
cat > run_cctv.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
python3 cctv_monitor.py
EOF
chmod +x run_cctv.sh

echo ""
echo "=========================================="
echo "  Installation complete!"
echo "=========================================="
echo ""
echo "Launch options:"
echo "  1. Application menu: 'CCTV Monitor'"
echo "  2. Script:           ./run_cctv.sh"
echo "  3. Direct:           python3 cctv_monitor.py"
echo ""
echo "Shortcuts:"
echo "  ESC  — exit fullscreen"
echo "  F11  — toggle fullscreen"
echo ""
