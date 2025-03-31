#!/bin/bash
pip install -r requirements.txt
flask db upgrade
gunicorn main:app
