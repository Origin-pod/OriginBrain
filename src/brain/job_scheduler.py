"""
Background Job Scheduler for OriginBrain.
Handles periodic and deferred tasks using Celery-like job queue.
"""

import threading
import time
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Callable, Any, Optional
from queue import PriorityQueue, Queue
from dataclasses import dataclass, field
from enum import Enum
import uuid

from src.db.db import BrainDB
from src.brain.cache_service import CacheService
from src.brain.curator import Curator
from src.brain.insights_engine import InsightsEngine
from src.brain.recommendation_engine import RecommendationEngine

logger = logging.getLogger(__name__)

class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"

@dataclass(order=True)
class Job:
    priority: int
    id: str = field(compare=False)
    func: Callable = field(compare=False)
    args: tuple = field(compare=False)
    kwargs: dict = field(compare=False)
    retry_count: int = field(default=0, compare=False)
    max_retries: int = field(default=3, compare=False)
    delay: float = field(default=0, compare=False)
    status: JobStatus = field(default=JobStatus.PENDING, compare=False)
    created_at: datetime = field(default_factory=datetime.now, compare=False)
    error_message: str = field(default="", compare=False)

class JobScheduler:
    """Background job scheduler with priority queue and retry support."""

    def __init__(self, num_workers: int = 3):
        """
        Initialize job scheduler.

        Args:
            num_workers: Number of worker threads
        """
        self.num_workers = num_workers
        self.job_queue = PriorityQueue()
        self.running = False
        self.workers: List[threading.Thread] = []
        self.jobs: Dict[str, Job] = {}
        self.completed_jobs: Dict[str, Job] = {}
        self.lock = threading.Lock()

        # Services
        self.db = BrainDB()
        self.cache = CacheService()
        self.curator = Curator()
        self.insights_engine = InsightsEngine()
        self.recommendation_engine = RecommendationEngine()

        # Statistics
        self.stats = {
            'total_jobs': 0,
            'completed_jobs': 0,
            'failed_jobs': 0,
            'active_workers': 0
        }

    def start(self):
        """Start the job scheduler."""
        if self.running:
            logger.warning("Job scheduler is already running")
            return

        self.running = True
        logger.info(f"Starting job scheduler with {self.num_workers} workers")

        # Start worker threads
        for i in range(self.num_workers):
            worker = threading.Thread(target=self._worker, name=f"JobWorker-{i}")
            worker.daemon = True
            worker.start()
            self.workers.append(worker)

        # Start periodic tasks thread
        periodic_thread = threading.Thread(target=self._periodic_tasks, name="PeriodicTasks")
        periodic_thread.daemon = True
        periodic_thread.start()

    def stop(self):
        """Stop the job scheduler."""
        self.running = False
        logger.info("Stopping job scheduler...")

        # Wait for workers to finish
        for worker in self.workers:
            worker.join(timeout=5)

        logger.info("Job scheduler stopped")

    def add_job(self, func: Callable, *args, priority: int = 5,
                max_retries: int = 3, delay: float = 0, **kwargs) -> str:
        """
        Add a job to the queue.

        Args:
            func: Function to execute
            *args: Function arguments
            priority: Job priority (0=highest, 10=lowest)
            max_retries: Maximum retry attempts
            delay: Delay before execution (seconds)
            **kwargs: Function keyword arguments

        Returns:
            Job ID
        """
        job_id = str(uuid.uuid4())
        job = Job(
            priority=priority,
            id=job_id,
            func=func,
            args=args,
            kwargs=kwargs,
            max_retries=max_retries,
            delay=delay
        )

        with self.lock:
            self.jobs[job_id] = job
            if delay > 0:
                # Schedule delayed execution
                threading.Timer(delay, self._queue_delayed_job, args=[job]).start()
            else:
                self.job_queue.put(job)
            self.stats['total_jobs'] += 1

        logger.info(f"Added job {job_id} with priority {priority}")
        return job_id

    def _queue_delayed_job(self, job: Job):
        """Queue a delayed job."""
        if self.running:
            with self.lock:
                if job.id in self.jobs:  # Job hasn't been cancelled
                    self.job_queue.put(job)

    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """
        Get job status and details.

        Args:
            job_id: Job ID

        Returns:
            Job details or None
        """
        with self.lock:
            job = self.jobs.get(job_id) or self.completed_jobs.get(job_id)
            if job:
                return {
                    'id': job.id,
                    'status': job.status.value,
                    'priority': job.priority,
                    'retry_count': job.retry_count,
                    'created_at': job.created_at.isoformat(),
                    'error_message': job.error_message
                }
        return None

    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a pending job.

        Args:
            job_id: Job ID

        Returns:
            True if cancelled
        """
        with self.lock:
            if job_id in self.jobs and self.jobs[job_id].status == JobStatus.PENDING:
                del self.jobs[job_id]
                logger.info(f"Cancelled job {job_id}")
                return True
        return False

    def _worker(self):
        """Worker thread function."""
        while self.running:
            try:
                # Get job from queue with timeout
                try:
                    job = self.job_queue.get(timeout=1)
                except:
                    continue

                with self.lock:
                    if job.id not in self.jobs:
                        # Job was cancelled
                        continue
                    self.stats['active_workers'] += 1

                # Execute job
                self._execute_job(job)

            except Exception as e:
                logger.error(f"Worker error: {e}")
            finally:
                with self.lock:
                    self.stats['active_workers'] -= 1

    def _execute_job(self, job: Job):
        """Execute a job."""
        job.status = JobStatus.RUNNING
        logger.info(f"Executing job {job.id}")

        try:
            # Execute the function
            result = job.func(*job.args, **job.kwargs)

            # Mark as completed
            job.status = JobStatus.COMPLETED
            with self.lock:
                self.completed_jobs[job.id] = job
                self.jobs.pop(job.id, None)
                self.stats['completed_jobs'] += 1

            logger.info(f"Job {job.id} completed successfully")

        except Exception as e:
            logger.error(f"Job {job.id} failed: {e}")
            job.error_message = str(e)

            # Retry logic
            if job.retry_count < job.max_retries:
                job.retry_count += 1
                job.status = JobStatus.RETRYING
                retry_delay = 2 ** job.retry_count  # Exponential backoff

                logger.info(f"Retrying job {job.id} in {retry_delay} seconds (attempt {job.retry_count})")
                threading.Timer(retry_delay, self._queue_delayed_job, args=[job]).start()
            else:
                job.status = JobStatus.FAILED
                with self.lock:
                    self.completed_jobs[job.id] = job
                    self.jobs.pop(job.id, None)
                    self.stats['failed_jobs'] += 1

                logger.error(f"Job {job.id} failed after {job.max_retries} retries")

    def _periodic_tasks(self):
        """Run periodic maintenance tasks."""
        while self.running:
            try:
                # Clean up old completed jobs (older than 1 hour)
                self._cleanup_old_jobs()

                # Periodic tasks run every 5 minutes
                self.run_periodic_tasks()

                # Sleep for 5 minutes
                time.sleep(300)

            except Exception as e:
                logger.error(f"Periodic task error: {e}")

    def _cleanup_old_jobs(self):
        """Clean up old completed jobs."""
        cutoff = datetime.now() - timedelta(hours=1)

        with self.lock:
            to_remove = []
            for job_id, job in self.completed_jobs.items():
                if job.created_at < cutoff:
                    to_remove.append(job_id)

            for job_id in to_remove:
                del self.completed_jobs[job_id]

            if to_remove:
                logger.info(f"Cleaned up {len(to_remove)} old completed jobs")

    def run_periodic_tasks(self):
        """Run periodic maintenance and processing tasks."""
        try:
            # Process consumption queue
            self.add_job(
                self._process_consumption_queue,
                priority=1  # High priority
            )

            # Update recommendations
            self.add_job(
                self._update_recommendations,
                priority=3
            )

            # Generate insights
            self.add_job(
                self._generate_insights,
                priority=5
            )

            # Warm cache
            self.add_job(
                self.cache.warm_cache,
                priority=8
            )

        except Exception as e:
            logger.error(f"Failed to schedule periodic tasks: {e}")

    # --- Job definitions ---

    def _process_consumption_queue(self):
        """Process the consumption queue for pending artifacts."""
        try:
            logger.info("Processing consumption queue")
            queue_items = self.db.get_consumption_queue(limit=50)

            for item in queue_items:
                try:
                    # Analyze artifact
                    artifact = self.db.get_artifact_extended(item['artifact_id'])
                    if artifact:
                        self.curator.analyze_artifact(item['artifact_id'])
                        # Update status
                        self.db.update_consumption_status(
                            item['artifact_id'],
                            'unconsumed',
                            auto_processed=True
                        )
                except Exception as e:
                    logger.error(f"Failed to process queue item {item['id']}: {e}")

            # Invalidate cache
            self.cache.invalidate_pattern('queue:*')

        except Exception as e:
            logger.error(f"Failed to process consumption queue: {e}")

    def _update_recommendations(self):
        """Update user recommendations."""
        try:
            logger.info("Updating recommendations")
            # This would typically get all users and update their recommendations
            # For now, we'll use a default user
            recommendations = self.recommendation_engine.get_personalized_queue(
                user_id="default",
                limit=20
            )

            # Cache recommendations
            self.cache.cache_recommendations("default", recommendations)

        except Exception as e:
            logger.error(f"Failed to update recommendations: {e}")

    def _generate_insights(self):
        """Generate periodic insights."""
        try:
            logger.info("Generating insights")
            insights = self.insights_engine.generate_personalized_insights(
                user_id="default",
                days_back=7
            )

            # Cache insights
            key = f"insights_{datetime.now().strftime('%Y%m%d')}"
            self.cache.cache_insights(key, insights)

        except Exception as e:
            logger.error(f"Failed to generate insights: {e}")

    # --- Public API for common jobs ---

    def schedule_artifact_analysis(self, artifact_id: str, priority: int = 3):
        """Schedule artifact analysis."""
        return self.add_job(
            self.curator.analyze_artifact,
            artifact_id,
            priority=priority
        )

    def schedule_relationship_update(self, artifact_id: str, priority: int = 4):
        """Schedule relationship update for artifact."""
        return self.add_job(
            self._update_relationships,
            artifact_id,
            priority=priority
        )

    def _update_relationships(self, artifact_id: str):
        """Update relationships for an artifact."""
        try:
            from src.brain.relationship_mapper import RelationshipMapper
            mapper = RelationshipMapper()
            mapper.discover_relationships(artifact_id)
        except Exception as e:
            logger.error(f"Failed to update relationships for {artifact_id}: {e}")

    def schedule_export_job(self, format_type: str, filters: dict = None, priority: int = 8):
        """Schedule an export job."""
        return self.add_job(
            self._perform_export,
            format_type,
            filters or {},
            priority=priority
        )

    def _perform_export(self, format_type: str, filters: dict):
        """Perform export job."""
        try:
            from src.brain.export_service import ExportService
            exporter = ExportService()
            result = exporter.export_artifacts(format_type, filters=filters)

            # Store result for download
            export_id = str(uuid.uuid4())
            self.cache.set('export', export_id, result, ttl=3600)

            return export_id
        except Exception as e:
            logger.error(f"Export job failed: {e}")
            raise

    def get_statistics(self) -> dict:
        """Get scheduler statistics."""
        with self.lock:
            stats = self.stats.copy()
            stats['queue_size'] = self.job_queue.qsize()
            stats['pending_jobs'] = len([j for j in self.jobs.values() if j.status == JobStatus.PENDING])
            stats['running_jobs'] = len([j for j in self.jobs.values() if j.status == JobStatus.RUNNING])
            return stats

# Global scheduler instance
scheduler = JobScheduler()