wget -O Mambaforge-Linux-x86_64.sh https://github.com/conda-forge/miniforge/releases/latest/download/Mambaforge-Linux-x86_64.sh
chmod +x Mambaforge-Linux-x86_64.sh
/bin/bash Mambaforge-Linux-x86_64.sh -f -b -p "~/.mamba"
rm "Mambaforge-Linux-x86_64.sh"
apt install redis-server
echo "Installing required dependencies..."
apt install -y curl build-essential

# Install Rust using rustup
echo "Installing Rust..."
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

apt install gnupg postgresql-common apt-transport-https lsb-release wget
/usr/share/postgresql-common/pgdg/apt.postgresql.org.sh
echo "deb https://packagecloud.io/timescale/timescaledb/ubuntu/ $(lsb_release -c -s) main" | sudo tee /etc/apt/sources.list.d/timescaledb.list

version=$(lsb_release -rs)

if (( $(echo "$version < 22.04" | bc -l) )); then
    wget --quiet -O - https://packagecloud.io/timescale/timescaledb/gpgkey | sudo apt-key add -
else
    wget --quiet -O - https://packagecloud.io/timescale/timescaledb/gpgkey | sudo gpg --dearmor -o /etc/apt/trusted.gpg.d/timescaledb.gpg
fi
apt update -y
apt install timescaledb-2-postgresql-17 postgresql-client-17
timescaledb-tune
systemctl restart postgresql
source "~/.bashrc"
mamba create -n "rewrite" python=3.9
mamba activate "rewrite"
cat requirements.txt | xargs -n 1 pip install --no-deps
pip install git+https://github.com/cop-discord/tools
pip install git+https://github.com/cop-discord/wavelink
pip install git+https://github.com/JuanBindez/pytubefix
git clone https://github.com/cop-discord/disdick ; cd disdick ; pip install .[voice]
pip install git+https://github.com/cloudwithax/pomice
apt install docker docker-compose -y
read -sp "Enter new PostgreSQL password: " new_password
echo

# Set the PostgreSQL username (default is usually 'postgres')
pg_user="postgres"

# Change the password using psql
psql -U "$pg_user" -c "ALTER USER $pg_user WITH PASSWORD '$new_password';"

# Check if the command was successful
if [ $? -eq 0 ]; then
    echo "Password changed successfully."
else
    echo "Failed to change password."
fi
echo "please setup the proxy-server now and make sure you add all the ipv6's you need (AKA READ THE README.MD IN THE PROXY SERVER)"