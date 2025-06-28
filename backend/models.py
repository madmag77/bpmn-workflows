from sqlalchemy import Column, String, DateTime, Text, JSON
from sqlalchemy.sql import func
import uuid

from .database import Base

class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    template = Column(String, nullable=False)
    thread_id = Column(String, nullable=False, unique=True)
    status = Column(String, nullable=False)
    query = Column(Text, nullable=True)
    result = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
