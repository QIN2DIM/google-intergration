from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import suppress
from dataclasses import dataclass
from dataclasses import field, asdict
from datetime import datetime
from pathlib import Path
from typing import Set, Optional

import pymongo

from services.oauth2.google import UserInfo
from services.settings import project, config

__all__ = ["MongoStorage", "DefaultWare", "MemoStorage"]


@dataclass
class MongoConfigWaitlist:
    uri: Optional[str] = "mongodb://localhost:27017/"
    db_name: Optional[str] = "waitlist-alpha"

    def __post_init__(self):
        with suppress(KeyError):
            mongo_waitlist_uri = config.mongo_waitlist_uri
            if mongo_waitlist_uri:
                self.uri = mongo_waitlist_uri


class Storage(ABC):
    """CRUD happy-man"""

    _data_model: UserInfo = None

    @abstractmethod
    def find(self, *args, **kwargs) -> bool | None:
        ...

    @abstractmethod
    def insert(self, *args, **kwargs):
        ...

    def flush_model(self, data_model: UserInfo):
        self._data_model = data_model


@dataclass
class MemoStorage(Storage):
    sink_path: Path = None

    _cached_emails: Set[str] | None = field(default_factory=set)

    @classmethod
    def from_default(cls):
        mo = cls(sink_path=project.waitlist_local_cache)
        if not mo.sink_path.exists():
            mo._cached_emails = set()
            mo._refresh_localdb()
        else:
            with open(mo.sink_path, "r", encoding="utf8") as file:
                mo._cached_emails = {line.strip() for line in file if line.strip()}
        return mo

    def _refresh_localdb(self):
        self.sink_path.write_text("\n".join(self._cached_emails), encoding="utf8")

    def find(self, email, *args, **kwargs) -> bool | None:
        if email and email in self._cached_emails:
            return True
        return False

    def insert(self, email, *args, **kwargs):
        self._cached_emails.add(email)
        self._refresh_localdb()


@dataclass
class MongoStorage(Storage):
    _COLLECTION_USERS = "users"

    _cursor = None
    _waitlist = None

    @classmethod
    def from_default(cls):
        """Only for Google OAuth response"""
        mo = cls()
        mo._config = MongoConfigWaitlist()
        mo._client = pymongo.MongoClient(mo._config.uri)
        mo._waitlist = mo._client.get_database(mo._config.db_name)
        mo._cursor = mo._waitlist.get_collection(mo._COLLECTION_USERS)
        return mo

    def find(self, email: str | None = None, *args, **kwargs) -> bool | None:
        email = email or self._data_model.email
        return self._cursor.find_one(filter={"email": email}, *args, **kwargs)

    def insert(self, *args, **kwargs) -> bool | None:
        # make dictionary from data model
        pending_data = asdict(self._data_model)
        # Date is automatically redirected to the UTC timezone
        pending_data.update({"_date": datetime.now(), "_accessed": False})

        result = self._cursor.insert_one(pending_data)
        try:
            return result.acknowledged
        except (AttributeError, TypeError):
            return None


_dw = {
    "memory": MemoStorage,
    "mongo": MongoStorage
}
DefaultWare = _dw[config.default_database]
