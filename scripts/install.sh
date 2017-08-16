#!/usr/bin/env bash

cd ..

python3 -m venv env
. env/bin/activate

pip install -r requirements.txt
deactivate