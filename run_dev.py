#!/usr/bin/env python3
"""Development runner - uses debug mode"""
from app import app

if __name__ == '__main__':
    app.run(debug=True, port=5000)