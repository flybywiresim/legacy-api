'''
Script to start the application in development mode.
It can be run with the following command:

"python3 run.py"
'''

from api import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host='0.0.0.0')
