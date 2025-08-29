import asyncio


class ProjectState:
    """
    A class to manage a shared dictionary (the "state") for a project.
    """

    def __init__(self):
        self._state = {}
        self._lock = asyncio.Lock()

    async def update_state(self, key: str, value: any):
        """
        Updates the state with a key-value pair.
        """
        async with self._lock:
            self._state[key] = value

    def get_state(self, key: str) -> any:
        """
        Retrieves a value from the state by key.
        """
        return self._state.get(key)

    def get_all_state(self) -> dict:
        """
        Retrieves the entire state dictionary.
        """
        return self._state.copy()
