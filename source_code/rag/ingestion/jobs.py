import threading
import uuid
from collections import OrderedDict

MAX_JOBS = 50


class IngestionJobs:
    """In-memory registry of background Ingestions, keeping running jobs and the most recent finished ones."""

    def __init__(self, knowledge_base):
        self._knowledge_base = knowledge_base
        self._jobs = OrderedDict()
        self._lock = threading.Lock()

    def start(self, path):
        job = {
            "id": uuid.uuid4().hex,
            "name": path.name,
            "status": "running",
            "stage": "queued",
            "progress": {"done": 0, "total": 0},
            "chunks": None,
            "error": None,
        }
        with self._lock:
            self._jobs[job["id"]] = job
            finished = [job_id for job_id, other in self._jobs.items() if other["status"] != "running"]
            for job_id in finished[: max(0, len(self._jobs) - MAX_JOBS)]:
                del self._jobs[job_id]
            snapshot = self._snapshot(job)
        threading.Thread(target=self._run, args=(job, path), daemon=True).start()
        return snapshot

    def get(self, job_id):
        with self._lock:
            job = self._jobs.get(job_id)
            return self._snapshot(job) if job else None

    def list(self):
        with self._lock:
            return [self._snapshot(job) for job in reversed(self._jobs.values())]

    def _run(self, job, path):
        def progress(stage, done=0, total=0):
            self._update(job, stage=stage, progress={"done": done, "total": total})

        try:
            result = self._knowledge_base.ingest(path, progress)
            self._update(job, status="done", stage="done", chunks=result["chunks"])
        except Exception as error:
            self._update(job, status="failed", error=str(error) or type(error).__name__)

    def _update(self, job, **changes):
        with self._lock:
            job.update(changes)

    @staticmethod
    def _snapshot(job):
        return {**job, "progress": dict(job["progress"])}
