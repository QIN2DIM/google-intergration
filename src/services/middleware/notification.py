import threading
import typing
from contextlib import suppress
from dataclasses import dataclass

import apprise
from loguru import logger

from services.settings import config
from utils.toolbox import from_dict_to_dataclass

__all__ = ["send"]


@dataclass
class AppriseAliasSMTP:
    # Private
    user: typing.Optional[str] = ""
    password: typing.Optional[str] = ""

    # Generic
    domain: typing.Optional[str] = "gmail.com"
    scheme: typing.Optional[str] = "mailtos"
    smtp: typing.Optional[str] = "smtp.gmail.com"
    name: typing.Optional[str] = "XLangAI"
    from_email: typing.Optional[str] = ""

    def __post_init__(self):
        if not self.from_email:
            self.from_email = f"{self.user}@{self.domain}"

    def notify(
        self,
        message: str,
        title: str,
        to_emails: typing.Union[str, typing.List[str]],
        servers: typing.Optional[typing.List[str]] = None,
    ):
        """

        :param servers:
        :param message:
        :param title:
        :param to_emails: Real mailbox that can receive messages
        :return:
        """
        if isinstance(to_emails, str):
            to_emails = [to_emails]
        if not servers:
            servers = []

        servers.extend(
            [
                f"{self.scheme}://{self.user}:{self.password}@{self.domain}?"
                f"smtp={self.smtp}&name={self.name}&from={self.from_email}&to={to_email}"
                for to_email in to_emails
            ]
        )

        apobj = apprise.Apprise()
        apobj.add(servers)
        threading.Thread(target=apobj.notify, kwargs={"body": message, "title": title}).start()
        logger.debug(f"send email to {to_emails}")


def send(*, to_email: str):
    try:
        smtp_config = config.apprise["smtp"]
    except KeyError as e:
        logger.error("Failed to get Apprise.smtp settings from system config.yaml", err=e.args)
        return False

    servers = []
    with suppress(KeyError):
        servers.extend(config.apprise["servers"])

    _message = "Congratulations, you have joined the Waitlist."
    _title = "XLangAI Waitlist"

    smtp_server: AppriseAliasSMTP = from_dict_to_dataclass(AppriseAliasSMTP, smtp_config)
    smtp_server.notify(message=_message, title=_title, to_emails=to_email, servers=servers)
