import llm
from .lib.horde_request import generate

@llm.hookimpl
def register_models(register):
    register(Horde())

class Horde(llm.Model):
    model_id = "horde"

    def execute(self, prompt, stream, response, conversation):
        gen = generate(prompt)
        return [x["text"] for x in gen["generations"]]
