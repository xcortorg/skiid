module.exports = {
    apps: [{
      name: 'evict.bot',
      script: 'npm',
      args: 'start',
      env: {
        NODE_ENV: 'production'
      }
    }]
  }