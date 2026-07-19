class FakeSession:
    def __init__(self):
        self.context_path = "scic"
        self.executed = []

    async def execute(self, instruction):
        self.executed.append(instruction)
        return [42]

    def enter(self, instruction):
        self.context_path = f"scic/{instruction}"

    def back(self):
        self.context_path = "scic"

    def reset(self):
        self.context_path = "scic"

    def describe(self, instruction=None):
        return {"type": "context", "name": instruction or "scic", "path": "/scic", "children": []}

    def list_context(self):
        return (
            {"type": "context", "name": "math", "description": "Math"},
            {"type": "executable", "name": "status", "description": "Status"},
        )


class FakeSCIC:
    def __init__(self):
        self.session = FakeSession()

    def create_session(self):
        return self.session

    def export_tree(self):
        return {"type": "context", "name": "scic", "children": []}
