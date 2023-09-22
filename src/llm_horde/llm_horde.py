import llm
from . import horde_request


@llm.hookimpl
def register_models(register):
    register(Horde())


class Horde(llm.Model):
    model_id = "horde"

    class Options(llm.Options):
        max_tokens: int = 80
        temperature: float = None
        top_k: int = None
        top_p: float = None

    def execute(self, prompt, stream, response, conversation):
        context = []
        if conversation:
            for resp in conversation.responses:
                context.append(f"{resp.prompt.prompt}")
                context.append(f"{resp.text()}")
        context = "\n".join(context)
        options = {"max_length": prompt.options.max_tokens}
        if prompt.options.temperature:
            options["temperature"] = prompt.options.temperature
        gen = horde_request.generate(context[-1024:] + prompt.prompt, options=options)
        return [x["text"] for x in gen["generations"]]
