"""
CareerLens — Gunicorn Production Configuration
Optimized for Render.com free tier (512 MB RAM, 0.1 vCPU shared)
"""

import multiprocessing
import os

# ── Binding ────────────────────────────────────────────────────────────────────
# Render injects $PORT; fallback to 10000 (Render default) or 5001 locally
bind = f"0.0.0.0:{os.environ.get('PORT', '10000')}"

# ── Workers ────────────────────────────────────────────────────────────────────
# Render free tier: keep workers low to fit in 512 MB
workers = 2
threads = 4
worker_class = "gthread"

# ── Timeouts ───────────────────────────────────────────────────────────────────
timeout = 120          # AI calls can take time
keepalive = 5
graceful_timeout = 30

# ── Logging ────────────────────────────────────────────────────────────────────
accesslog = "-"        # stdout → Render log stream
errorlog = "-"         # stderr → Render log stream
loglevel = "info"
access_log_format = '%(h)s "%(r)s" %(s)s %(b)s %(D)sµs'

# ── Security ───────────────────────────────────────────────────────────────────
forwarded_allow_ips = "*"    # Render sits behind a proxy
secure_scheme_headers = {"X-Forwarded-Proto": "https"}

# ── Process naming ─────────────────────────────────────────────────────────────
proc_name = "careerlens"

# ── Lifecycle hooks ────────────────────────────────────────────────────────────
def on_starting(server):
    """Initialize the database before workers fork."""
    from database import init_db
    init_db()
    server.log.info("CareerLens database initialized ✓")
