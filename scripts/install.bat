echo Make sure you have at least Python 3.4 installed

cd..

python -m venv env
call env\scripts\activate.bat

pip install -r requirements.txt
deactivate