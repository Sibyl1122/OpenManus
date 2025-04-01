"""
Job Execution Engine for OpenManus.
"""

import asyncio
import datetime
import logging
import uuid
from typing import Dict, Any, List, Optional, Callable, Coroutine, Union

from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Job, Task, ToolUse, JobStatus, TaskStatus

logger = logging.getLogger(__name__)


class JobEngine:
    """Job Execution Engine for running and tracking jobs."""

    def __init__(self):
        """Initialize the job engine."""
        self._jobs = {}  # Dict to track running jobs by ID
        self._stopped = False

    def create_job(self, description: str = None) -> str:
        """
        Create a new job in the database.

        Args:
            description: Optional description of the job

        Returns:
            job_id: Unique identifier for the job
        """
        job_id = f"job_{uuid.uuid4().hex[:8]}"

        with get_db() as db:
            job = Job(
                job_id=job_id,
                description=description,
                status=JobStatus.PENDING,
            )
            db.add(job)
            db.commit()
            db.refresh(job)

        return job_id

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job details by ID.

        Args:
            job_id: Job ID to retrieve

        Returns:
            Dict containing job details or None if not found
        """
        with get_db() as db:
            job = db.query(Job).filter(Job.job_id == job_id).first()
            if job:
                return job.to_dict()
            return None

    def list_jobs(self, status: Optional[JobStatus] = None) -> List[Dict[str, Any]]:
        """
        List all jobs, optionally filtered by status.

        Args:
            status: Optional status filter

        Returns:
            List of job dictionaries
        """
        with get_db() as db:
            query = db.query(Job)
            if status:
                query = query.filter(Job.status == status)

            jobs = query.order_by(Job.created_at.desc()).all()
            return [job.to_dict() for job in jobs]

    def add_task(self, job_id: str, content: str) -> int:
        """
        Add a task to a job.

        Args:
            job_id: Job ID to add task to
            content: Task content/description

        Returns:
            task_id: ID of the created task
        """
        with get_db() as db:
            job = db.query(Job).filter(Job.job_id == job_id).first()
            if not job:
                raise ValueError(f"Job with ID {job_id} not found")

            task = Task(
                content=content,
                status=TaskStatus.PENDING,
                job_id=job.id
            )
            db.add(task)
            db.commit()
            db.refresh(task)

            return task.id

    def record_tool_use(self, task_id: int, tool_name: str, args: Dict[str, Any], result: str = None) -> int:
        """
        Record a tool use within a task.

        Args:
            task_id: Task ID to add tool use to
            tool_name: Name of the tool used
            args: Arguments passed to the tool
            result: Result of the tool execution

        Returns:
            tool_use_id: ID of the created tool use record
        """
        with get_db() as db:
            task = db.query(Task).filter(Task.id == task_id).first()
            if not task:
                raise ValueError(f"Task with ID {task_id} not found")

            tool_use = ToolUse(
                tool_name=tool_name,
                args=args,
                result=result,
                task_id=task.id
            )
            db.add(tool_use)
            db.commit()
            db.refresh(tool_use)

            return tool_use.id

    def update_tool_result(self, tool_use_id: int, result: str) -> None:
        """
        Update the result of a tool use.

        Args:
            tool_use_id: Tool use ID to update
            result: New result to set
        """
        with get_db() as db:
            tool_use = db.query(ToolUse).filter(ToolUse.id == tool_use_id).first()
            if not tool_use:
                raise ValueError(f"ToolUse with ID {tool_use_id} not found")

            tool_use.result = result
            db.commit()

    async def run_job(self, job_id: str, task_handler: Callable[[int, str], Coroutine[Any, Any, bool]]) -> bool:
        """
        Run a job asynchronously with the provided task handler.

        Args:
            job_id: Job ID to run
            task_handler: Async function that takes task_id and content and returns success boolean

        Returns:
            success: True if job completed successfully, False otherwise
        """
        # Get job from database
        with get_db() as db:
            job = db.query(Job).filter(Job.job_id == job_id).first()
            if not job:
                logger.error(f"Job with ID {job_id} not found")
                return False

            # Mark job as running
            job.start()
            db.commit()

            # Get all tasks for this job
            tasks = db.query(Task).filter(Task.job_id == job.id).all()
            task_ids = [(task.id, task.content) for task in tasks]

        # Track job in memory
        self._jobs[job_id] = {
            "tasks_total": len(task_ids),
            "tasks_completed": 0,
            "tasks_failed": 0,
            "started_at": datetime.datetime.utcnow(),
        }

        success = True

        # Process each task
        for task_id, content in task_ids:
            if self._stopped:
                break

            try:
                # Update task status
                with get_db() as db:
                    task = db.query(Task).filter(Task.id == task_id).first()
                    task.start()
                    db.commit()

                # Execute task handler
                task_success = await task_handler(task_id, content)

                # Update task status based on result
                with get_db() as db:
                    task = db.query(Task).filter(Task.id == task_id).first()
                    if task_success:
                        task.complete()
                        self._jobs[job_id]["tasks_completed"] += 1
                    else:
                        task.fail()
                        self._jobs[job_id]["tasks_failed"] += 1
                        success = False
                    db.commit()

            except Exception as e:
                logger.exception(f"Error processing task {task_id}: {str(e)}")

                # Mark task as failed
                with get_db() as db:
                    task = db.query(Task).filter(Task.id == task_id).first()
                    task.fail()
                    db.commit()

                self._jobs[job_id]["tasks_failed"] += 1
                success = False

        # Mark job as completed or failed
        with get_db() as db:
            job = db.query(Job).filter(Job.job_id == job_id).first()
            if self._stopped:
                job.cancel()
            elif success:
                job.complete()
            else:
                job.fail()
            db.commit()

        # Cleanup
        if job_id in self._jobs:
            del self._jobs[job_id]

        return success

    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a running job.

        Args:
            job_id: Job ID to cancel

        Returns:
            success: True if job was cancelled, False if job wasn't running or not found
        """
        with get_db() as db:
            job = db.query(Job).filter(Job.job_id == job_id).first()
            if not job or job.status != JobStatus.RUNNING:
                return False

            job.cancel()

            # Cancel any running tasks
            for task in db.query(Task).filter(
                Task.job_id == job.id,
                Task.status == TaskStatus.RUNNING
            ).all():
                task.cancel()

            db.commit()

        # Remove from tracking if present
        if job_id in self._jobs:
            del self._jobs[job_id]

        return True

    def get_job_stats(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get statistics for a running job.

        Args:
            job_id: Job ID to get stats for

        Returns:
            Dict of stats or None if job not running
        """
        if job_id not in self._jobs:
            return None

        stats = self._jobs[job_id].copy()
        stats["runtime"] = (datetime.datetime.utcnow() - stats["started_at"]).total_seconds()
        return stats

    def shutdown(self) -> None:
        """Shutdown the job engine, cancelling all running jobs."""
        self._stopped = True

        # Cancel all running jobs
        with get_db() as db:
            for job in db.query(Job).filter(Job.status == JobStatus.RUNNING).all():
                job.cancel()

                # Cancel any running tasks
                for task in db.query(Task).filter(
                    Task.job_id == job.id,
                    Task.status == TaskStatus.RUNNING
                ).all():
                    task.cancel()

            db.commit()

        # Clear tracking dict
        self._jobs.clear()


# Global instance
job_engine = JobEngine()
