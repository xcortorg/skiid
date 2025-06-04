module.exports = {
    apps: [{
      name: "cdn.evict.bot",
      script: "./target/release/local_cdn",
      exec_mode: "fork",
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: "1G",
      env: {
        NODE_ENV: "production",
      }
    }]
  }