#!/bin/bash
gunicorn -t 60 app:app
