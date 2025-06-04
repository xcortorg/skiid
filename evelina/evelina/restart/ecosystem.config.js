module.exports = {
  apps: [
    {
      name: "restart-bot",
      cwd: "/root/evelina/restart",                       // where restart.py lives
      script: "restart.py",                                
      interpreter: "/root/evelina/.venv/bin/python3",      // ← point here, not restart/.venv
      env: {
        RESTART_BOT_TOKEN: "OTQyNjk0OTUyOTE0MjY0MDk1.GdhIYd._RRcNjW9jPQXe_Ib6Shn1sPOMyqQ4VmKmealvg"
      }
    }
  ]
}