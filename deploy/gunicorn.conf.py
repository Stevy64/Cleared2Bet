"""Gunicorn — bind Unix socket (nginx) ou TCP local."""
import multiprocessing
import os

bind = os.environ.get('GUNICORN_BIND', 'unix:/run/cleared2bet/gunicorn.sock')
workers = int(os.environ.get('GUNICORN_WORKERS', max(2, multiprocessing.cpu_count() * 2 + 1)))
threads = int(os.environ.get('GUNICORN_THREADS', '2'))
timeout = int(os.environ.get('GUNICORN_TIMEOUT', '60'))
keepalive = 5
worker_class = 'gthread'
accesslog = '-'
errorlog = '-'
capture_output = True
preload_app = True
