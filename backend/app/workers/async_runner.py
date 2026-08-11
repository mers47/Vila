import asyncio
from celery import Task


class AsyncTask(Task):
    def __call__(self, *args, **kwargs):
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return loop.create_task(self.run(*args, **kwargs))
        return loop.run_until_complete(self.run(*args, **kwargs))

    async def run(self, *args, **kwargs):
        raise NotImplementedError