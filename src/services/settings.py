import json
import os
import sys
from dataclasses import dataclass, field
from os.path import dirname
from pathlib import Path
from typing import Dict, Any, Literal

import yaml
from loguru import logger

from utils import from_dict_to_dataclass, init_log


@dataclass
class Project:
    src_point = Path(dirname(dirname(__file__)))
    root_point = src_point.parent
    config_system = src_point.joinpath("system.yaml")

    database = root_point.joinpath("database")
    secret = database.joinpath("secrets")
    waitlist_local_cache = database.joinpath("waitlist.emails.txt")

    config_google_oauth_client_secret = secret.joinpath("client_secret_google.json")

    logs = root_point.joinpath("logs")

    _pending_events = None

    def __post_init__(self):
        for hook in [self.secret]:
            os.makedirs(hook, exist_ok=True)

    def diagnose(self):
        if not self.config_system.exists():
            logger.error(f"系统配置文件缺失，无法运行项目", filename=self.config_system.name)
            logger.success(f"自动生成默认配置文件，你可能需要按需修改它再重启项目", filepath=self.config_system)
            self.config_system.write_text(yaml.safe_dump(self.template))
            sys.exit(1)

        if not self.config_google_oauth_client_secret.exists():
            logger.error(
                "核心配置缺失，无法正常启动 GoogleOAuth 服务", miss_path=self.config_google_oauth_client_secret
            )
            logger.warning(
                "请前往 Google Console 获取密钥文件，修改文件名并放置到指定路径下",
                console="https://console.cloud.google.com/apis/credentials",
                rename=self.config_google_oauth_client_secret.name,
                target=str(self.config_google_oauth_client_secret),
            )

    @property
    def template(self):
        return {
            "apprise": {
                "smtp": {
                    "user": "",
                    "password": "",
                    "domain": "gmail.com",
                    "scheme": "mailtos",
                    "smtp": "smtp.gmail.com",
                    "name": "WaitListAI",
                    "from_email": "",  # Gmail alias, such as `no-reply@waitlist.ai`
                },
                "servers": [],
            },
            "oauth2": {
                "google": {
                    "insecure": True,
                    "scopes": [
                        "https://www.googleapis.com/auth/userinfo.email",
                        "https://www.googleapis.com/auth/userinfo.profile",
                        "openid",
                    ],
                }
            },
            "default_database": "memory",
            "mongo_waitlist_uri": "mongodb://localhost:27017/",
        }

    def register_service(self, service):
        # -- skip --
        logger.success("注册服务", service=service)
        self._pending_events = service


@dataclass
class Config:
    apprise: Dict[str, Any] = field(default_factory=dict)
    oauth2: Dict[str, Any] = field(default_factory=dict)
    mongo_waitlist_uri: str = ""
    default_database: Literal["memory", "mongo"] = "memory"

    @classmethod
    def from_yaml(cls, fp: Path):
        if not fp.exists():
            logger.error("你应该先初始化项目目录再创建系统配置")
            fp.write_text("", encoding="utf8")
        datas = yaml.safe_load(fp.read_text(encoding="utf8"))
        return from_dict_to_dataclass(cls, datas)

    def show(self):
        print(f"载入运行配置 >> \n{json.dumps(self.__dict__, indent=4)}")


project = Project()

init_log(
    error=project.logs.joinpath("error.log"),
    runtime=project.logs.joinpath("runtime.log"),
    serialize=project.logs.joinpath("serialize.log"),
)
project.diagnose()

config = Config.from_yaml(fp=project.config_system)
