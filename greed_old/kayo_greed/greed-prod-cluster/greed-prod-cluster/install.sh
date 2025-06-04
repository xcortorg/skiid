sudo apt update

curl -fsSL https://pkg.cloudflareclient.com/pubkey.gpg | sudo gpg --yes --dearmor --output /usr/share/keyrings/cloudflare-warp-archive-keyring.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/cloudflare-warp-archive-keyring.gpg] https://pkg.cloudflareclient.com/ $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/cloudflare-client.list
sudo apt-get update && sudo apt-get install cloudflare-warp -y # done
source "$HOME/.cargo/env"
maturin develop && cd ..

warp-cli register
warp-cli mode proxy
warp-cli proxy port 7483
warp-cli connect

sudo apt install imagemagick
sudo apt install redis-server postgresql postgresql-contrib -y
sudo systemctl start postgresql.service
sudo -i -u postgres
psql
CREATE DATABASE greed;
ALTER USER postgres with encrypted password 'aiem6hP-zXtt0m22x35m';
\q
exit

sudo apt install redis-server
redis-server --requirepass "H?vanmir09Mason12screen-rzan" --port 6379
