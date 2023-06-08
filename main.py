# -*- coding: utf-8 -*-
# Time       : 2023/6/9 1:44
# Author     : QIN2DIM
# Github     : https://github.com/QIN2DIM
# Description:
import json
import os
from dataclasses import dataclass
from typing import List, Optional

import flask
import requests
from flask import jsonify, redirect
from flask.views import View
from google_auth_oauthlib.flow import Flow
import secrets

app = flask.Flask(__name__)
app.secret_key = secrets.token_hex()


@dataclass
class GoogleOAuthCredentials:
    client_id: str
    client_secret: str
    scopes: List[str]
    token: str
    token_uri: str
    refresh_token: Optional[str] = ""
    expiry: Optional[str] = ""


def _navigator():
    return """
        <div><a href='/auth/google/authorize'>Google OAuth</a></div>
        <div><a href='/auth/google/revoke'>Revoke Credentials</a></div>
        <div><a href='/auth/google/clear'>Clear Credentials</a></div>
        """


class GoogleOAuth(View):
    # This variable specifies the name of a file that contains the OAuth 2.0
    # information for this application, including its client_id and client_secret.
    CLIENT_SECRETS_FILE = "google_oauth/client_secret.json"

    # This OAuth 2.0 access scope allows for full read/write access to the
    # authenticated user's account and requires requests to use an SSL connection.
    SCOPES = [
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
        "openid",
    ]

    def __init__(self):
        super().__init__()
        self._credentials = "go_credentials"

        app.add_url_rule("/", view_func=_navigator, methods=["GET"])
        app.add_url_rule("/auth/google/authorize", view_func=self.authorize, methods=["GET"])
        app.add_url_rule("/auth/google/connect", view_func=self.oauth2callback, methods=["GET"])
        app.add_url_rule("/auth/google/revoke", view_func=self.revoke, methods=["GET"])
        app.add_url_rule("/auth/google/clear", view_func=self.clear_credentials, methods=["GET"])

    def authorize(self):
        """Access this route and redirect to Google's authentication domain"""
        flow = Flow.from_client_secrets_file(self.CLIENT_SECRETS_FILE, scopes=self.SCOPES)
        flow.redirect_uri = flask.url_for("oauth2callback", _external=True)
        authorization_url, state = flow.authorization_url(
            access_type="offline", include_granted_scopes="true"
        )

        # Store the state so the callback can verify the auth server response.
        flask.session["state"] = state

        return redirect(authorization_url)

    def oauth2callback(self):
        """Receive authorization information from Google servers"""
        state = flask.session["state"]
        flow = Flow.from_client_secrets_file(
            self.CLIENT_SECRETS_FILE, scopes=self.SCOPES, state=state
        )
        flow.redirect_uri = flask.url_for("oauth2callback", _external=True)

        # Use the authorization server's response to fetch the OAuth 2.0 tokens.
        authorization_response = flask.request.url
        flow.fetch_token(authorization_response=authorization_response)

        # Store credentials in the session.
        # In a production app, you likely want to save these credentials in a persistent database instead.
        credentials = GoogleOAuthCredentials(**json.loads(flow.credentials.to_json()))
        flask.session[self._credentials] = credentials.__dict__

        return jsonify(credentials.__dict__)

    def revoke(self):
        if self._credentials not in flask.session:
            _href = flask.url_for("authorize")
            return (
                f'You need to <a href="{_href}">authorize</a> '
                f"before testing the code to revoke credentials."
            )
        credentials = GoogleOAuthCredentials(**flask.session[self._credentials])
        resp = requests.post(
            "https://oauth2.googleapis.com/revoke",
            params={"token": credentials.token},
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        if resp.status_code == 200:
            return "Credentials successfully revoked."
        return "An error occurred."

    def clear_credentials(self):
        if self._credentials in flask.session:
            del flask.session[self._credentials]
        return "Credentials successfully cleared"


GoogleOAuth()

if __name__ == "__main__":
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    app.run("localhost", 8000, debug=True)
