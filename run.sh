#!/bin/bash
set -e

git pull https://oauth2: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@github.com/samubd/coffeeMMachineSimulator.git

cd coffeeMMachineSimulator

pip install --no-cache-dir -r requirements.txt

python3 main_new.py
