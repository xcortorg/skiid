#!/bin/bash

# Detect OS
OS=$(uname | tr '[:upper:]' '[:lower:]')

install_redis_linux() {
    DISTRO=$(lsb_release -is | tr '[:upper:]' '[:lower:]')
    echo "Detected Linux distribution: $DISTRO"

    if [[ "$DISTRO" == "ubuntu" || "$DISTRO" == "debian" ]]; then
        echo "Installing Redis on Ubuntu/Debian..."
        sudo apt update && sudo apt install redis-server -y
        sudo systemctl enable redis
        sudo systemctl start redis
    else
        echo "Unsupported Linux distribution. Please install Redis manually."
        exit 1
    fi
}

install_redis_macos() {
    echo "Installing Redis on macOS..."
    # Check if Homebrew is installed, if not, install it
    if ! command -v brew &> /dev/null; then
        echo "Homebrew not found. Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi
    brew update && brew install redis
    brew services start redis
}

install_redis_windows() {
    echo "Installing Redis on Windows via WSL..."
    if ! command -v apt &> /dev/null; then
        echo "WSL not detected. Please install WSL and try again."
        exit 1
    fi
    sudo apt update && sudo apt install redis-server -y
    sudo service redis-server start
}

# Run the appropriate installation function
case "$OS" in
    "linux")
        install_redis_linux
        ;;
    "darwin")
        install_redis_macos
        ;;
    "windowsnt" | "cygwin" | "msys")
        install_redis_windows
        ;;
    *)
        echo "Unsupported OS: $OS"
        exit 1
        ;;
esac

echo "Redis installation completed successfully!"

