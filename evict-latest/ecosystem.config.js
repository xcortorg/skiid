module.exports = {
    apps: [
      {
        name: 'evict',
        script: '/root/evict/.venv/bin/python3.12',
        args: ['main.py'],
        cwd: '/root/evict',
        env: {
          NODE_ENV: 'production',
          PYTHONPATH: '/root/evict'
        }
      },
    ]
  };
  