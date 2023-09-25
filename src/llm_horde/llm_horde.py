import re

import llm
from . import horde_request


@llm.hookimpl
def register_models(register):
    global MODELS
    try:
        MODELS = horde_request.get_models()
        for model in MODELS:
            register(ModelFactory.model(f"{Horde.model_prefix}/{model}"))
        register(ModelFactory.model(Horde.model_prefix))
    except Exception as e:
        print("llm-horde plugin error in register_models():", repr(e))
        return


class Horde(llm.Model):
    model_prefix = "horde"
    needs_key = "aihorde"
    key_env_var = "AIHORDE_KEY"

    def __init__(self):
        super().__init__()

    class Options(llm.Options):
        max_tokens: int = 80
        temperature: float = None
        top_k: int = None
        top_p: float = None
        key: str = None
        pattern: str = ""
        debug: bool = False
        instruct: str = "auto"

    instruct_auto = {
        "synthia": "synthia",
        "mythomax": "alpaca",
        "holomax": "alpaca",
        "mlewd": "alpaca",
        "airo": "alpaca",
        "wizardcoder": "alpaca",
        "wizardlm": "vicuna",
        "alion": "metharme",
        "erebus": "completion",
    }

    def execute(self, prompt, stream, response, conversation):
        response.response_json = {}
        if self.model_id == self.model_prefix:
            if conversation and not prompt.options.pattern:
                for resp in conversation.responses[::-1]:
                    if resp.prompt.options.pattern:
                        prompt.options.pattern = resp.prompt.options.pattern
                        break
            models = [
                model
                for model in MODELS
                if re.search(prompt.options.pattern, model, flags=re.IGNORECASE)
            ]
            if not models:
                print(f"Model matching {prompt.options.pattern} not found")
        else:
            models = [self.model_id[len(self.model_prefix) + 1 :]]
        if prompt.options.debug:
            print(models)

        prompt_text = self.build_prompt_text(prompt, response, conversation, models[0])

        options = {"max_length": prompt.options.max_tokens}
        if prompt.options.temperature:
            options["temperature"] = prompt.options.temperature
        if prompt.options.top_k:
            options["top_k"] = prompt.options.top_k
        if prompt.options.top_p:
            options["top_p"] = prompt.options.top_p

        apikey = llm.get_key(
            explicit_key=prompt.options.key,
            key_alias=self.needs_key,
            env_var=self.key_env_var,
        )
        horde_request.APIKEY = apikey or horde_request.ANON_APIKEY
        gen = horde_request.generate(prompt=prompt_text, models=models, options=options)
        response.response_json["models"] = [x["model"] for x in gen["generations"]]
        response.response_json["kudos"] = gen["kudos"]
        if prompt.options.debug:
            print("Response:", repr(gen), "\n---")
        return [x["text"] for x in gen["generations"]]

    def build_prompt_text(self, prompt, response, conversation, model):
        templates = {
            "synthia": {
                "system": "\nSYSTEM: {system}",
                "user": "\nUSER: {prompt}\nASSISTANT: ",
            },
            "vicuna": {
                "system": "\n[SYSTEM]\n{system}",
                "user": "\n### USER:\n{prompt}\n### ASSISTANT:\n",
            },
            "metharme": {
                "system": "\n<|system|>{system}",
                "user": "\n<|user|>{prompt}\n<|model|>",
            },
            "alpaca": {
                "system": "\n{system}\n",
                "user": "\n### Instruction:\n{prompt}\n\n### Response:\n",
            },
            "completion": {
                "system": "{system}",
                "user": "{prompt}",
            },
        }
        if prompt.options.instruct == "auto":
            for key, value in self.instruct_auto.items():
                if key.lower() in model.lower():
                    instruct = value
                    break
            else:
                instruct = "alpaca"
        else:
            instruct = prompt.options.instruct
        response.response_json["instruct"] = instruct

        context = []
        if conversation:
            if conversation.responses and conversation.responses[0].prompt.system:
                context.append(
                    templates[instruct]["system"].format(
                        system=conversation.responses[0].prompt.system
                    )
                )
            for resp in conversation.responses:
                context.append(
                    templates[instruct]["user"].format(prompt=resp.prompt.prompt)
                )
                context.append(resp.text())
        context = "".join(context)

        if prompt.prompt == "" or instruct == "completion":
            prompt_text = context + prompt.prompt
        else:
            prompt_text = context
            if prompt.system:
                prompt_text += templates[instruct]["system"].format(
                    system=prompt.system
                )
            prompt_text += templates[instruct]["user"].format(prompt=prompt.prompt)
        if prompt.options.debug:
            print("Full prompt:\n", prompt_text, "\n---")
        return prompt_text

    def __repr__(self):
        return f"AI Horde: {self.model_id}"


class ModelFactory:
    @classmethod
    def model(cls, model_id):
        return type(
            "AI Horde", (Horde,), {"model_id": model_id, "model_name": "AI Horde"}
        )()
