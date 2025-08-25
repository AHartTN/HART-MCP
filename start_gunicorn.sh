#!/bin/bash
export FLASK_APP=server:app
gunicorn --bind 0.0.0.0:8080 server:app --workers 4 --log-level info