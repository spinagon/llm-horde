import re
import importlib
import json
from typing import Optional

from pydantic import Field
import llm

from . import horde_request


@llm.hookimpl
def register_models(register):
    global MODELS
    try:
        MODELS = horde_request.get_models()
        for model in MODELS:
            register(Horde(model_id=f"{Horde.model_prefix}/{model}", model_name=model))
        register(Horde(model_id=Horde.model_prefix, model_name=Horde.model_prefix))
    except Exception as e:
        print("llm-horde plugin error in register_models():", repr(e))
        return


class Horde(llm.Model):
    model_prefix = "horde"
    needs_key = "aihorde"
    key_env_var = "AIHORDE_KEY"

    def __init__(self, model_id, model_name):
        self.model_id = model_id
        self.model_name = model_name

    def __str__(self):
        return "AI Horde: {}".format(self.model_id)

    class Options(llm.Options):
        max_tokens: Optional[int] = Field(ge=16, le=512, default=120)
        temperature: Optional[float] = Field(ge=0, le=5, default=None)
        top_k: Optional[int] = Field(ge=0, le=100, default=None)
        top_p: Optional[float] = Field(ge=0.001, le=1, default=None)
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
        "xwin": "vicuna",
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
            models = [self.model_name]
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
        response.model.model_id = f"{self.model_prefix}/{gen['generations'][0]['model']}"
        response.response_json["kudos"] = gen["kudos"]
        if prompt.options.debug:
            print("Response:", repr(gen), "\n---")
        return [x["text"] for x in gen["generations"]]

    def build_prompt_text(self, prompt, response, conversation, model):
        templates = json.loads(
            importlib.resources.files("llm_horde")
            .joinpath("templates.json")
            .read_text()
        )
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

        if prompt.system is None:
            prompt.system = templates[instruct].get("system_default", None)

        context = rebuild_conversation(conversation, templates[instruct])

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


def rebuild_conversation(conversation, template):
    context = []
    if conversation:
        if conversation.responses and conversation.responses[0].prompt.system:
            context.append(
                template["system"].format(
                    system=conversation.responses[0].prompt.system
                )
            )
        for resp in conversation.responses:
            if resp.prompt.prompt:
                context.append(
                    template["user"].format(prompt=resp.prompt.prompt)
                )
            context.append(resp.text())
    return "".join(context)
