class FlagNotFoundError(Exception):
    def __init__(self, key: str) -> None:
        super().__init__(f"Flag '{key}' not found")
        self.key = key


class FlagAlreadyExistsError(Exception):
    def __init__(self, key: str) -> None:
        super().__init__(f"Flag '{key}' already exists")
        self.key = key
