module.exports = {
    apps: [{
      name: 'cname.evict.bot',
      script: 'pnpm',
      args: 'start',
      env: {
        NODE_ENV: 'production'
      }
    }]
  }