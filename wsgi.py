'''
Script to start the applicaiton in produciton.
The file "api.ini" is used to configure the WSGI server.
'''

from api import create_app

app = create_app()

if __name__ == "__main__":
    app.run()
