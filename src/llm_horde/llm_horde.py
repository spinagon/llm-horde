import json
from typing import Optional

from pydantic import Field
import llm

from . import horde_request


@llm.hookimpl
def register_models(register):
    try:
        for model in horde_request.get_models():
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

    def execute(self, prompt, stream, response, conversation):
        response.response_json = {}
        if self.model_id == self.model_prefix:
            if conversation and not prompt.options.pattern:
                for resp in conversation.responses[::-1]:
                    if resp.prompt.options.pattern:
                        prompt.options.pattern = resp.prompt.options.pattern
                        break
            models = horde_request.match_model(prompt.options.pattern)
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

        response.model.model_id = (
            f"{self.model_prefix}/{gen['generations'][0]['model']}"
        )
        response.response_json["kudos"] = gen["kudos"]

        if prompt.options.debug:
            print("Response:", repr(gen), "\n---")

        return [x["text"] for x in gen["generations"]]

    def build_prompt_text(self, prompt, response, conversation, model_name):
        templates = horde_request.templates()
        instruct = horde_request.get_instruct(
            mode=prompt.options.instruct, model_name=model_name
        )
        response.response_json["instruct"] = instruct

        if prompt.system is None:
            prompt.system = templates[instruct].get("system_default", None)

        messages = []
        if conversation:
            if conversation.responses and conversation.responses[0].prompt.system:
                messages.append(
                    {
                        "role": "system",
                        "content": conversation.responses[0].prompt.system,
                    }
                )
            for resp in conversation.responses:
                if resp.prompt.prompt:
                    messages.append({"role": "user", "content": resp.prompt.prompt})
                messages.append({"role": "assistant", "content": resp.text()})

        if prompt.prompt == "" or instruct == "completion":
            messages.append({"role": "completion", "content": prompt.prompt})
        else:
            if prompt.system:
                messages.append({"role": "system", "content": prompt.system})
            messages.append({"role": "user", "content": prompt.prompt})
            messages.append({"role": "assistant", "content": ""})

        prompt_text = horde_request.build_conversation(messages, templates[instruct])

        if prompt.options.debug:
            print("Full prompt:\n", prompt_text, "\n---")

        return prompt_text

    def __repr__(self):
        return f"AI Horde: {self.model_id}"
