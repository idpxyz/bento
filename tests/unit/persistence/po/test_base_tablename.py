from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from bento.persistence.po.base import Base as SA_Base


def test_declared_attr_generates_lower_tablename():
    class UserModel(SA_Base):
        id: Mapped[str] = mapped_column(String, primary_key=True)

    assert UserModel.__tablename__ == "usermodel"
