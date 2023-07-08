# -*- coding: utf-8 -*-
# Time       : 2023/7/7 12:14
# Author     : QIN2DIM
# Github     : https://github.com/QIN2DIM
# Description:
import flask

from apis import routing

app = flask.Flask(__name__)
routing(app, test_google_oauth2=True)

if __name__ == "__main__":
    app.run("localhost", 8000, debug=True)
