# **bleed inspired bot**











# **To do**

- [ ] Add the rest of of booster role commands 7/22
- [ ] More shit idk















## **Requirements**

- Python 3.12
- PostgreSQL
- Basic understanding of the terminal

## **Getting Started**

1. **Clone the Repository:**
   To get started, run the following command:

   ```bash
   git clone https://github.com/hiddeout/mono-opensource.git
   ```

2. **Install PostgreSQL:**
   Download and install PostgreSQL from [here](https://www.postgresql.org/download/windows/) or for your OS of choice.

   ```bash
   sudo apt-get update
   sudo apt-get install postgresql
   ```

3. **Create a Database:**
   Run the following command in your terminal or CMD:

   - For Linux:
     ```bash
     sudo -i -u postgres
     psql
     ALTER USER postgres with encrypted password 'admin';
     ```
   - For Windows:
     ```bash
     psql -U postgres
     ```

   Then inside the postgres terminal, run:

   ```sql
   CREATE DATABASE bleed;
   ```
4. 

## **Install the Dependencies **

Open a terminal in this directory and run:

```bash
pyenv install 3.12.7
pyenv global 3.12.7
python3.12 -m venv .venv
pip install -r requirements.txt
pip uninstall discord.py && pip uninstall meow.py && pip install git+https://github.com/parelite/discord.py
source .venv/bin/activate
```

If this fails on windows make sure Python is installed and added to PATH.

Once installed, run:

```bash
python launcher.py
```

if you want to  contribute to the project, feel free to fork it and make a pull request.


> install pyenv on ubuntu: https://medium.com/@aashari/easy-to-follow-guide-of-how-to-install-pyenv-on-ubuntu-a3730af8d7f0

## **Install And Setup Cloudflare Warped**

```bash
# Add Cloudflare GPG key
curl https://pkg.cloudflareclient.com/pubkey.gpg | sudo gpg --yes --dearmor --output /usr/share/keyrings/cloudflare-warp-archive-keyring.gpg

# Add the repository
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/cloudflare-warp-archive-keyring.gpg] https://pkg.cloudflareclient.com/ $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/cloudflare-client.list

# Update package list
sudo apt-get update

# Install WARP
sudo apt-get install cloudflare-warp

# Register and configure WARP using warp-cli
warp-cli registration new
warp-cli mode proxy
warp-cli proxy port 7483
warp-cli connect
```

Note: Use `warp-cli` instead of `warp` for all commands. You can see available commands by running `warp-cli --help`.

# Verify connection status
warp-cli status
```
## **Install Playwright After Installing Requirements**

```bash
playwright install
playwright install-deps
```

```
git config --global user.email "hiddeoutcollective@gmail.com"
git config --global user.name "fiji"
```

# extra 

/discord/ext/commands/core.py
        self.brief: Optional[str] = kwargs.get('brief')
        self.usage: Optional[str] = kwargs.get('usage')
        self.rest_is_raw: bool = kwargs.get('rest_is_raw', False)
        self.aliases: Union[List[str], Tuple[str]] = kwargs.get('aliases', [])
        self.extras: Dict[Any, Any] = kwargs.get('extras', {})
        self.example: Optional[str] = kwargs.get('example')
        self.information: Optional[str] = kwargs.get('information')
        self.notes: Optional[str] = kwargs.get('notes')
        self.parameters: Dict[Any, Any] = kwargs.get('parameters', {})

# extra 
/discord/ext/commands/core.py

    @discord.utils.cached_property
    def permissions(self) -> Optional[List[str]]:
        perms = [perm for check in self.checks if getattr(check, '__closure__', None) for cell in check.__closure__ if isinstance(cell.cell_contents, dict) for perm, val in cell.cell_contents.items() if val]
        return perms if perms else None

# install redis

```bash
sudo apt-get install lsb-release curl gpg
curl -fsSL https://packages.redis.io/gpg | sudo gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg
sudo chmod 644 /usr/share/keyrings/redis-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/redis.list
sudo apt-get update
sudo apt-get install redis
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

```bash
apt install net-tools
sudo apt-get update
sudo apt-get install libmagickwand-dev
sudo apt install ffmpeg
```
