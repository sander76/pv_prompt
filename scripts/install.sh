#!/usr/bin/env bash

cd ..

python -m venv env
. env/bin/activate

pip install -r requirements.txt
deactivate