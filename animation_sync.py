"""Small presentation-only barrier for Ursina animation handles.

Poll after Ursina updates its sequences. In 8.3.0, a nominal animation duration
can be shorter than Sequence.duration; timers are not completion signals.
"""


class AnimationCompletion:
    def __init__(self, handles, callback):
        self.handles = []
        for handle in handles:
            if isinstance(handle, (tuple, list)):
                self.handles.extend(h for h in handle if h is not None)
            elif handle is not None:
                self.handles.append(handle)
        self.callback = callback
        self.completed = False
        self.cancelled = False

    def poll(self):
        if self.completed or self.cancelled:
            return
        if not all(h.finished and all(h.func_finished_statuses) for h in self.handles):
            return
        self.completed = True
        callback, self.callback = self.callback, None
        callback()

    def cancel(self):
        self.cancelled = True
        self.callback = None
        for handle in self.handles:
            handle.kill()
