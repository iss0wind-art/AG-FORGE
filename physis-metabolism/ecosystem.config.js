module.exports = {
  apps: [
    {
      name: 'physis-metabolism',
      script: '/home/nas/AG-Forge/.venv/bin/python',
      args: '/home/nas/AG-Forge/physis-metabolism/metabolism.py',
      cwd: '/home/nas/AG-Forge/physis-metabolism',
      interpreter: 'none',
      autorestart: true,
      max_restarts: 10,
      min_uptime: '30s',
      restart_delay: 5000,
      kill_timeout: 8000,
      out_file: '/home/nas/AG-Forge/physis-metabolism/logs/metabolism.out.log',
      error_file: '/home/nas/AG-Forge/physis-metabolism/logs/metabolism.err.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      env: {
        PHYSIS_TICK_SECONDS: '5',
        PHYSIS_SWEEP_INTERVAL_TICKS: '720',
        PHYSIS_DUCKDB_PATH: '/home/nas/AG-Forge/physis_memory/physis_brain.duckdb',
        PHYSIS_CHROMADB_PATH: '/home/nas/AG-Forge/physis_memory/.chromadb',
        PHYSIS_STIMULI_QUEUE: '/home/nas/AG-Forge/physis-metabolism/stimuli',
        PHYSIS_REDIS_URL: 'redis://127.0.0.1:6379/0',
        PHYSIS_REDIS_CHANNEL: 'physis:stimulus',
        PHYSIS_FORGETTING_THRESHOLD: '0.2',
      },
    },
  ],
};
