from typing import Dict, Callable


class APIMethod:
    def __init__(self, func: Callable, config: Dict = None) -> None:
        self.func: Callable = func
        self.config: Dict = config
