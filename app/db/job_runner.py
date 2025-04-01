"""
Job Runner Service for OpenManus.
"""

import asyncio
import json
import logging
import time
import traceback
from typing import Dict, Any, List, Optional, Callable, Coroutine

from app.db.job_engine import job_engine
from app.db.models import Job, Task, ToolUse
from app.logger import logger

class JobRunner:
    """Service for running jobs asynchronously."""

    def __init__(self):
        """Initialize the job runner."""
        self._running_jobs = {}
        self._stopping = False

    async def start_job(self, job_id: str) -> bool:
        """
        Start running a job in the background.

        Args:
            job_id: ID of the job to run

        Returns:
            success: True if job was started, False otherwise
        """
        # Check if job already running
        if job_id in self._running_jobs:
            logger.warning(f"Job {job_id} is already running")
            return False

        # Get the job to make sure it exists
        job_data = job_engine.get_job(job_id)
        if not job_data:
            logger.error(f"Job {job_id} not found")
            return False

        # Start the job in a background task
        task = asyncio.create_task(self._run_job(job_id))
        self._running_jobs[job_id] = task

        logger.info(f"Started job {job_id}")
        return True

    async def _run_job(self, job_id: str) -> None:
        """
        Run a job and process its tasks.

        Args:
            job_id: ID of the job to run
        """
        try:
            # Run the job using the job engine
            await job_engine.run_job(job_id, self._process_task)
        except Exception as e:
            logger.exception(f"Error running job {job_id}: {str(e)}")
        finally:
            # Remove from running jobs
            if job_id in self._running_jobs:
                del self._running_jobs[job_id]

    async def _process_task(self, task_id: int, content: str) -> bool:
        """
        Process a single task.

        Args:
            task_id: ID of the task to process
            content: Content of the task

        Returns:
            success: True if task processed successfully, False otherwise
        """
        try:
            logger.info(f"Processing task {task_id}: {content}")

            # Here you would typically:
            # 1. Parse the task content into actions
            # 2. Execute those actions using tools
            # 3. Record the results

            # Simple demonstration - we'll record a dummy tool use
            tool_use_id = job_engine.record_tool_use(
                task_id=task_id,
                tool_name="demo_tool",
                args={"query": content},
                result=None
            )

            # Simulate processing time
            await asyncio.sleep(2)

            # Update the tool result
            job_engine.update_tool_result(
                tool_use_id=tool_use_id,
                result=json.dumps({"success": True, "message": f"Processed task: {content}"})
            )

            return True

        except Exception as e:
            logger.exception(f"Error processing task {task_id}: {str(e)}")
            return False

    async def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a running job.

        Args:
            job_id: ID of the job to cancel

        Returns:
            success: True if job was cancelled, False otherwise
        """
        # Check if job is running in this service
        if job_id not in self._running_jobs:
            logger.warning(f"Job {job_id} is not running in this service")
            return False

        # Cancel the job in the job engine
        success = job_engine.cancel_job(job_id)

        # Cancel the task if it's still running
        task = self._running_jobs.get(job_id)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Remove from running jobs
        if job_id in self._running_jobs:
            del self._running_jobs[job_id]

        return success

    async def shutdown(self) -> None:
        """Shutdown the job runner service."""
        self._stopping = True

        # Cancel all running jobs
        job_ids = list(self._running_jobs.keys())
        for job_id in job_ids:
            await self.cancel_job(job_id)

        # Tell the job engine to shutdown
        job_engine.shutdown()


# Global instance
job_runner = JobRunner()
