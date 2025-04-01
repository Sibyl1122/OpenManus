"""
JobTool for creating and interacting with persisted jobs.
"""

import json
import logging
from typing import Dict, Any, List, Optional

from app.db.job_engine import job_engine
from app.db.job_runner import job_runner
from app.db.models import JobStatus
from app.tool.base import BaseTool



class JobTool(BaseTool):
    """
    Tool for creating and managing jobs in the OpenManus system.
    """

    name: str = "job"
    description: str = "Create and manage jobs and tasks for automated execution"

    async def create_job(self, description: str = None) -> Dict[str, Any]:
        """
        Create a new job.

        Args:
            description: Optional description of the job

        Returns:
            Dict containing the job_id
        """
        job_id = job_engine.create_job(description)
        return {"job_id": job_id, "status": "created"}

    async def add_task(self, job_id: str, content: str) -> Dict[str, Any]:
        """
        Add a task to a job.

        Args:
            job_id: ID of the job to add the task to
            content: Task content/description

        Returns:
            Dict containing the task_id
        """
        try:
            task_id = job_engine.add_task(job_id, content)
            return {"task_id": task_id, "status": "added"}
        except ValueError as e:
            return {"error": str(e)}

    async def get_job(self, job_id: str) -> Dict[str, Any]:
        """
        Get details about a job.

        Args:
            job_id: ID of the job to get details for

        Returns:
            Dict containing job details
        """
        job = job_engine.get_job(job_id)
        if job:
            return job
        return {"error": f"Job with ID {job_id} not found"}

    async def list_jobs(self, status: str = None) -> Dict[str, Any]:
        """
        List all jobs, optionally filtered by status.

        Args:
            status: Optional status filter (pending, running, completed, failed, cancelled)

        Returns:
            Dict containing a list of jobs
        """
        job_status = None
        if status:
            try:
                job_status = JobStatus(status.lower())
            except ValueError:
                return {"error": f"Invalid status: {status}"}

        jobs = job_engine.list_jobs(job_status)
        return {"jobs": jobs}

    async def run_job(self, job_id: str) -> Dict[str, Any]:
        """
        Start running a job.

        Args:
            job_id: ID of the job to run

        Returns:
            Dict containing status of the operation
        """
        # Start the job using the job runner
        success = await job_runner.start_job(job_id)

        if success:
            return {"message": f"Job {job_id} started successfully", "status": "running"}
        return {"error": f"Failed to start job {job_id}"}

    async def cancel_job(self, job_id: str) -> Dict[str, Any]:
        """
        Cancel a running job.

        Args:
            job_id: ID of the job to cancel

        Returns:
            Dict containing status of the operation
        """
        # Try to cancel using the job runner first (for active jobs)
        success = await job_runner.cancel_job(job_id)

        if success:
            return {"message": f"Job {job_id} cancelled", "status": "cancelled"}

        # If not found in job runner, try the job engine
        success = job_engine.cancel_job(job_id)
        if success:
            return {"message": f"Job {job_id} cancelled", "status": "cancelled"}

        return {"error": f"Could not cancel job {job_id} - not running or not found"}

    async def get_job_stats(self, job_id: str) -> Dict[str, Any]:
        """
        Get statistics for a running job.

        Args:
            job_id: ID of the job to get statistics for

        Returns:
            Dict containing job statistics
        """
        stats = job_engine.get_job_stats(job_id)
        if stats:
            return stats

        # Check if job exists but is not running
        job = job_engine.get_job(job_id)
        if job:
            return {"message": f"Job {job_id} is not currently running", "status": job.get("status")}

        return {"error": f"Job with ID {job_id} not found"}

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the job tool with the given arguments."""
        action = kwargs.pop("action", "get_job")

        handlers = {
            "create_job": self.create_job,
            "add_task": self.add_task,
            "get_job": self.get_job,
            "list_jobs": self.list_jobs,
            "run_job": self.run_job,
            "cancel_job": self.cancel_job,
            "get_job_stats": self.get_job_stats,
        }

        handler = handlers.get(action)
        if not handler:
            return {"error": f"Unknown action: {action}"}

        return await handler(**kwargs)

    def to_param(self) -> Dict[str, Any]:
        """Convert the tool to a parameter definition."""
        return {
            "function": {
                "name": self.name,
                "description": "Create and manage jobs and tasks for automated execution",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "description": "The action to perform (create_job, add_task, get_job, list_jobs, run_job, cancel_job, get_job_stats)",
                            "enum": ["create_job", "add_task", "get_job", "list_jobs", "run_job", "cancel_job", "get_job_stats"]
                        },
                        "job_id": {
                            "type": "string",
                            "description": "Job ID for the operation"
                        },
                        "description": {
                            "type": "string",
                            "description": "Description for a new job"
                        },
                        "content": {
                            "type": "string",
                            "description": "Content for a new task"
                        },
                        "status": {
                            "type": "string",
                            "description": "Status filter for listing jobs (pending, running, completed, failed, cancelled)",
                            "enum": ["pending", "running", "completed", "failed", "cancelled"]
                        }
                    },
                    "required": ["action"]
                }
            }
        }
