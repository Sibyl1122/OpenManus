"""
SQLAlchemy models for the database layer.
"""

import datetime
import enum
import json
from typing import Dict, Any, Optional, List

from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Enum, JSON
from sqlalchemy.orm import relationship

from app.db.database import Base


class JobStatus(str, enum.Enum):
    """Job execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskStatus(str, enum.Enum):
    """Task execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Job(Base):
    """Job model representing a complete execution job"""
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(50), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(JobStatus), default=JobStatus.PENDING, nullable=False)
    start_time = Column(DateTime, default=None, nullable=True)
    end_time = Column(DateTime, default=None, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    tasks = relationship("Task", back_populates="job", cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary"""
        return {
            "id": self.id,
            "job_id": self.job_id,
            "description": self.description,
            "status": self.status.value if self.status else None,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "tasks": [task.to_dict() for task in self.tasks],
        }

    def start(self) -> None:
        """Mark job as started"""
        self.status = JobStatus.RUNNING
        self.start_time = datetime.datetime.utcnow()

    def complete(self) -> None:
        """Mark job as completed"""
        self.status = JobStatus.COMPLETED
        self.end_time = datetime.datetime.utcnow()

    def fail(self) -> None:
        """Mark job as failed"""
        self.status = JobStatus.FAILED
        self.end_time = datetime.datetime.utcnow()

    def cancel(self) -> None:
        """Mark job as cancelled"""
        self.status = JobStatus.CANCELLED
        self.end_time = datetime.datetime.utcnow()

##一轮对话就有一个task
## 一轮对话的产物: 一次think, 一次toolUse
## 若没有tooluse,则认为任务结束，这次think应该被保存成文档
class Task(Base):
    """Task model representing a subtask within a job"""
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    think = Column(Text, nullable=True)
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING, nullable=False)
    start_time = Column(DateTime, default=None, nullable=True)
    end_time = Column(DateTime, default=None, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Foreign keys
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)

    # Relationships
    job = relationship("Job", back_populates="tasks")
    tool_uses = relationship("ToolUse", back_populates="task", cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary"""
        return {
            "id": self.id,
            "content": self.content,
            "think": self.think,
            "status": self.status.value if self.status else None,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "job_id": self.job_id,
            "tool_uses": [tool_use.to_dict() for tool_use in self.tool_uses],
        }

    def start(self) -> None:
        """Mark task as started"""
        self.status = TaskStatus.RUNNING
        self.start_time = datetime.datetime.utcnow()

    def complete(self) -> None:
        """Mark task as completed"""
        self.status = TaskStatus.COMPLETED
        self.end_time = datetime.datetime.utcnow()

    def fail(self) -> None:
        """Mark task as failed"""
        self.status = TaskStatus.FAILED
        self.end_time = datetime.datetime.utcnow()

    def cancel(self) -> None:
        """Mark task as cancelled"""
        self.status = TaskStatus.CANCELLED
        self.end_time = datetime.datetime.utcnow()


class ToolUse(Base):
    """ToolUse model representing a tool usage within a task"""
    __tablename__ = "tool_uses"

    id = Column(Integer, primary_key=True, index=True)
    tool_name = Column(String(100), nullable=False)
    args = Column(JSON, nullable=True)
    result = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Foreign keys
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)

    # Relationships
    task = relationship("Task", back_populates="tool_uses")

    def to_dict(self) -> Dict[str, Any]:
        """Convert tool use to dictionary"""
        return {
            "id": self.id,
            "tool_name": self.tool_name,
            "args": self.args,
            "result": self.result,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "task_id": self.task_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolUse":
        """Create a ToolUse instance from a dictionary"""
        return cls(
            tool_name=data.get("tool_name"),
            args=data.get("args"),
            result=data.get("result"),
            task_id=data.get("task_id"),
        )
