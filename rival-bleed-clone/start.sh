#!/bin/bash

set -e  # Exit on any error

# Helper function to compare Ubuntu versions
version_lte() {
    [ "$(printf '%s\n' "$1" "$2" | sort -V | head -n1)" == "$1" ]
}

echo "Updating package lists and installing prerequisites..."
sudo apt update && sudo apt install -y gnupg postgresql-common apt-transport-https lsb-release wget

echo "Running PostgreSQL repository setup script..."
sudo /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh

echo "Installing PostgreSQL server development package..."
sudo apt install -y postgresql-server-dev-16

# Add TimescaleDB repository
echo "Adding TimescaleDB repository..."
echo "deb https://packagecloud.io/timescale/timescaledb/ubuntu/ $(lsb_release -c -s) main" | sudo tee /etc/apt/sources.list.d/timescaledb.list

# Get Ubuntu version number
UBUNTU_VERSION=$(lsb_release -rs)

# Add GPG key conditionally based on Ubuntu version
if version_lte "$UBUNTU_VERSION" "21.10"; then
    echo "Adding TimescaleDB GPG key..."
    wget --quiet -O - https://packagecloud.io/timescale/timescaledb/gpgkey | sudo gpg --dearmor -o /etc/apt/trusted.gpg.d/timescaledb.gpg
else
    echo "Skipping GPG key addition for Ubuntu $UBUNTU_VERSION."
fi

echo "Updating package lists..."
sudo apt update

echo "Installing TimescaleDB and PostgreSQL client..."
sudo apt install -y timescaledb-2-postgresql-16 postgresql-client-16

echo "Running TimescaleDB tuning tool..."
sudo timescaledb-tune --quiet --yes

echo "Restarting PostgreSQL service..."
sudo systemctl restart postgresql

echo "Setting password for PostgreSQL 'postgres' user..."
sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD '001278870';"

echo "Installation and setup complete. You can now run the bot using cd bot ; python main.py"
