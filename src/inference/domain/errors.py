class MlInferenceError(Exception):
    def __init__(self, message: str = "An unexpected ML inference error occurred"):
        self.message = message
        super().__init__(self.message)


class PermanentError(MlInferenceError):
    pass


class InvalidTaskPayloadError(MlInferenceError):
    def __init__(self, details: str):
        self.details = details
        super().__init__(f"invalid task payload: {self.details}")


class TaskPayloadError(MlInferenceError):
    def __init__(self, details: str):
        self.details = details
        super().__init__(self.message)
