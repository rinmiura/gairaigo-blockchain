import asyncio


class Loop(list):

    def __init__(self):
        self.event_loop = asyncio.get_event_loop()
        super().__init__()

    def append(self, worker, *args, **kwargs):
        super().append(self.event_loop.create_task(worker(*args, **kwargs)))

    def join(self):
        self.event_loop.run_forever()
