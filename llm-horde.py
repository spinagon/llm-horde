import llm

@llm.hookimpl
def register_models(register):
    register(Horde())

class Horde(llm.Model):
    model_id = "horde"

    def execute(self, prompt, stream, response, conversation):
        return ["hello world"]
