class Tool:
    def __init__(self, name: str = "", description: str = ""):
        self.name = name
        self.description = description

    def execute(self, *args, **kwargs):
        raise NotImplementedError()
