module.exports = {
  apps: [
    {
      name: 'clusters',
      script: '/root/greed/.venv/bin/python3.10',
      args: ['-m', 'rival'],
      cwd: '/root/greed',
      env: {
        NODE_ENV: 'production',
        PYTHONPATH: '/root/greed'
      }
    },
    {
      name: 'bot-cluster-0',
      script: '/root/greed/.venv/bin/python3.10',
      args: ['run.py', '1'],
      cwd: '/root/greed',
      env: {
        CLUSTER_ID: '1',
        PYTHONPATH: '/root/greed'
      }
    },
    {
      name: 'bot-cluster-1',
      script: '/root/greed/.venv/bin/python3.10',
      args: ['run.py', '2'],
      cwd: '/root/greed',
      env: {
        CLUSTER_ID: '2',
        PYTHONPATH: '/root/greed'
      }
    },
    {
      name: 'bot-cluster-2',
      script: '/root/greed/.venv/bin/python3.10',
      args: ['run.py', '3'],
      cwd: '/root/greed',
      env: {
        CLUSTER_ID: '3',
        PYTHONPATH: '/root/greed'
      }
    },
    {
      name: 'bot-cluster-3',
      script: '/root/greed/.venv/bin/python3.10',
      args: ['run.py', '4'],
      cwd: '/root/greed',
      env: {
        CLUSTER_ID: '4',
        PYTHONPATH: '/root/greed'
      }
    }
  ]
};
