import os
import typing
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import requests
from loguru import logger

from services.settings import project, config
from utils.toolbox import from_dict_to_dataclass

_CREDENTIAL_ID = "go_credentials"


@dataclass
class Credentials:
    client_id: str
    client_secret: str
    scopes: List[str]
    token: str
    token_uri: str
    refresh_token: Optional[str] = ""
    expiry: Optional[str] = ""


@dataclass
class UserInfo:
    # GET - https://www.googleapis.com/oauth2/v2/userinfo
    id: str
    email: str
    verified_email: bool
    name: str
    given_name: str
    picture: str
    locale: str


@dataclass
class GoogleUser:
    auth: Credentials
    info: Optional[UserInfo] = None

    @classmethod
    @logger.catch
    def from_session(cls, session, credentials_id: Optional[str] = _CREDENTIAL_ID):
        """
        :type session: flask.globals.SessionMixin
        :param session:
        :param credentials_id:
        :return:
        """
        return cls(auth=from_dict_to_credentials(session[credentials_id]))

    @property
    def headers(self):
        headers = {
            "Authorization": f"Bearer {self.auth.token}",
            "Content-type": "application/x-www-form-urlencoded;charset=UTF-8",
        }
        return headers

    def get_userinfo(self) -> Optional[UserInfo]:
        url = "https://www.googleapis.com/oauth2/v2/userinfo"
        resp = requests.get(url, headers=self.headers)
        self.info = from_dict_to_userinfo(resp.json())
        return self.info


def from_dict_to_userinfo(data: dict) -> UserInfo:
    return from_dict_to_dataclass(UserInfo, data)


def from_dict_to_credentials(data: dict) -> Credentials:
    return from_dict_to_dataclass(Credentials, data)


@dataclass
class OAuth2Service:
    # This variable specifies the name of a file that contains the OAuth 2.0
    # information for this application, including its client_id and client_secret.
    CLIENT_SECRETS_FILE: Path = None

    # This OAuth 2.0 access scope allows for full read/write access to the
    # authenticated user's account and requires requests to use an SSL connection.
    SCOPES: typing.Optional[list] = field(default_factory=list)

    _credential_id: typing.Optional[str] = _CREDENTIAL_ID

    def __post_init__(self):
        _insecure = "insecure"
        _scopes = "scopes"

        self.CLIENT_SECRETS_FILE = project.config_google_oauth_client_secret
        self.SCOPES = [
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
            "openid",
        ]

        try:
            go_settings: typing.Dict[str, typing.Any] = config.oauth2["google"]
        except KeyError as e:
            logger.error(
                "Failed to get Google OAuth2.0 settings from system config.yaml", err=e.args
            )
        else:
            # ::insecure:: False IF production else True
            if go_settings.get(_insecure, True) is True:
                os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
                self._scheme = "http"
            else:
                os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "0"
                self._scheme = "https"
            # ::scopes::
            self.SCOPES = go_settings.get(_scopes, self.SCOPES)
            # ::env:: Assume the UPPER val as an ENV val
            for k in go_settings:
                k: str
                if k.isupper():
                    os.environ[k] = go_settings[k]
