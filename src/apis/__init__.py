# -*- coding: utf-8 -*-
# Time       : 2023/7/7 12:24
# Author     : QIN2DIM
# Github     : https://github.com/QIN2DIM
# Description:
import secrets

from flask import Flask

from .waitlist_alpha import GoogleOAuth, apply_navigator


def _register_google_oauth(backend: Flask, *, test_google_oauth2: bool = True):
    oauth = GoogleOAuth()

    # -- debug --
    if test_google_oauth2:
        apply_navigator(backend, rule="/")

    # -- register --
    backend.add_url_rule("/auth/google/authorize", view_func=oauth.authorize, methods=["GET"])
    backend.add_url_rule("/auth/google/connect", view_func=oauth.oauth2callback, methods=["GET"])
    backend.add_url_rule("/auth/google/revoke", view_func=oauth.revoke, methods=["GET"])
    backend.add_url_rule("/auth/google/joined", view_func=oauth.joined, methods=["GET"])

    # -- skip --
    # project.register_service(oauth)


def routing(backend: Flask, **kwargs):
    backend.secret_key = secrets.token_hex()
    _register_google_oauth(backend, **kwargs)
