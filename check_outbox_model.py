"""Check OutboxRecord model registration."""

import sys

sys.path.insert(0, "/workspace/bento")

from bento.persistence.sqlalchemy.base import Base as FrameworkBase
from bento.persistence.sqlalchemy.outbox_sql import OutboxRecord

print("OutboxRecord class info:")
print(f"  __tablename__: {OutboxRecord.__tablename__}")
print(f"  __table__: {OutboxRecord.__table__}")
print(f"  Base: {OutboxRecord.__bases__}")

print("\nFrameworkBase metadata tables:")
for table_name in FrameworkBase.metadata.tables:
    print(f"  - {table_name}")

if not FrameworkBase.metadata.tables:
    print("  ❌ No tables registered!")
