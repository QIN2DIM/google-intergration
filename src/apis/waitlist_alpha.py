import json

import flask
import requests
from flask import redirect, jsonify
from flask.views import View
from google_auth_oauthlib.flow import Flow
from loguru import logger

from services.middleware import notify
from services.oauth2.google import from_dict_to_credentials, GoogleUser, OAuth2Service
from services.storage.waitlsit import DefaultWare


class GoogleOAuth(OAuth2Service, View):
    def __init__(self):
        super().__init__()
        self._storage = DefaultWare.from_default()

    def _url_for(self, endpoint: str) -> str:
        return flask.url_for(endpoint, _external=True, _scheme=self._scheme)

    @logger.catch
    def authorize(self):
        """Access this route and redirect to Google's authentication domain"""
        flow = Flow.from_client_secrets_file(str(self.CLIENT_SECRETS_FILE), scopes=self.SCOPES)
        flow.redirect_uri = self._url_for("oauth2callback")
        authorization_url, state = flow.authorization_url(include_granted_scopes="true")

        # Store the state so the callback can verify the auth server response.
        flask.session["state"] = state

        return redirect(authorization_url)

    def oauth2callback(self):
        """Receive authorization information from Google servers"""
        try:
            state = flask.session["state"]
        except KeyError:
            return redirect("/")
        flow = Flow.from_client_secrets_file(
            str(self.CLIENT_SECRETS_FILE), scopes=self.SCOPES, state=state
        )
        flow.redirect_uri = self._url_for("oauth2callback")

        # Use the authorization server's response to fetch the OAuth 2.0 tokens.
        authorization_response = flask.request.url
        flow.fetch_token(authorization_response=authorization_response)

        # Store credentials in the session.
        # In a production app, you likely want to save these credentials in a persistent database instead.
        credentials = from_dict_to_credentials(json.loads(flow.credentials.to_json()))
        flask.session[self._credential_id] = credentials.__dict__

        return redirect(self._url_for("joined"))

    def revoke(self):
        if self._credential_id not in flask.session:
            _href = self._url_for("authorize")
            return (
                f'You need to <a href="{_href}">authorize</a> '
                f"before testing the code to revoke credentials."
            )

        credentials = from_dict_to_credentials(flask.session[self._credential_id])
        resp = requests.post(
            "https://oauth2.googleapis.com/revoke",
            params={"token": credentials.token},
            headers={"content-type": "application/x-www-form-urlencoded"},
        )

        if resp.status_code == 200:
            del flask.session[self._credential_id]
            return "Credentials successfully revoked."
        return "An error occurred."

    def joined(self):
        if self._credential_id not in flask.session:
            return jsonify({"result": False, "msg": "Application authorization failed."})

        user = GoogleUser.from_session(flask.session, self._credential_id)
        info = user.get_userinfo()
        username, email = info.name, info.email

        # Hook user object to database
        self._storage.flush_model(info)

        # new user into Waitlist
        if not self._storage.find(email):
            self._storage.insert(email)
            logger.success(f"New user join the waitlist", username=username, email=email)
            # send message to user
            notify(to_email=email)
            return jsonify(
                {"result": True, "msg": "Congratulations, you have joined the Waitlist."}
            )

        # user already in the Waitlist
        logger.info("user re-access waitlist page", username=username, email=email)
        return jsonify(
            {"result": True, "msg": "You have already joined the Waitlist.", "email": email}
        )


def apply_navigator(app, rule: str = "/"):
    def _navigator():
        return flask.render_template_string(
            """
    <!DOCTYPE html>
    <html lang="zh">
    <head>
        <title>WaitlistAI</title>
        <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate"/>
    </head>
    <body>
        <div><a href='/auth/google/authorize'>Continue with Google</a></div>
        <div><a href='/auth/google/revoke'>Revoke Credentials</a></div>
        <div><a href='https://mail.google.com/mail/u/0/#search/from%3A(no-reply%40ros.services)' target="_blank">Check Notification</a></div>
    </body>
    </html>
    """
        )

    app.add_url_rule(rule, view_func=_navigator, methods=["GET"])
