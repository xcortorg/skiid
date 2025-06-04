module.exports = {
    apps: [
      {
        name: 'status',
        script: 'python3.12',
        args: 'ipc.py',
        interpreter: 'none', // This tells PM2 not to use Node.js to run the script
      },
],
  };
