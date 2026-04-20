from redis import Redis
from rq import Queue

from color_analysis.config import get_settings


class RedisQueue:
    def __init__(self) -> None:
        settings = get_settings()
        self.connection = Redis.from_url(settings.redis_url)
        self.queue = Queue("analyze", connection=self.connection)

    def enqueue_analysis(self, session_id: str) -> str:
        job = self.queue.enqueue("color_analysis.workers.analyze.run_analysis", session_id)
        return job.id

    def set_result_cache(self, session_id: str, value: str, ttl_seconds: int = 300) -> None:
        self.connection.setex(f"session:{session_id}:result", ttl_seconds, value)

    def delete_session_keys(self, session_id: str) -> None:
        keys = self.connection.keys(f"session:{session_id}:*")
        if keys:
            self.connection.delete(*keys)
