import json
from typing import Optional
import time

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
        max_tokens: int = Field(ge=16, le=512, default=256)
        temperature: float | None = Field(
            None, description="Temperature value.", ge=0.0, le=5.0
        )
        tfs: float | None = Field(
            None, description="Tail free sampling value.", ge=0.0, le=1.0
        )
        top_a: float | None = Field(
            None, description="Top-a sampling value.", ge=0.0, le=1.0
        )
        top_k: int | None = Field(
            None, description="Top-k sampling value.", ge=0, le=100
        )
        top_p: float | None = Field(
            None, description="Top-p sampling value.", ge=0.001, le=1.0
        )
        typical: float | None = Field(
            None, description="Typical sampling value.", ge=0.0, le=1.0
        )

        key: str = None
        pattern: str = ""
        debug: bool = False
        instruct: str = "auto"

    def execute(self, prompt, stream, response, conversation):
        response.response_json = {}
        if self.model_name not in horde_request.get_models() or prompt.options.pattern:
            models = horde_request.match_model(prompt.options.pattern)
            if not models:
                print(f"Model matching {prompt.options.pattern} not found")
        else:
            models = [self.model_name]
        if prompt.options.debug:
            print("Models:", models)

        options = {}
        if conversation and conversation.responses:
            options.update(
                conversation.responses[-1].prompt.options.model_dump(exclude_unset=True)
            )
            options.pop("debug", None)

        options.update(
            prompt.options.model_dump(exclude_unset=True, exclude_defaults=True)
        )
        for key, value in options.items():
            setattr(prompt.options, key, value)
        options.pop("max_tokens", None)
        options["max_length"] = prompt.options.max_tokens

        if prompt.options.debug:
            print("Options:", options)

        if self.model_name in horde_request.get_models():
            model_name = self.model_name
        else:
            # choose at pseudorandom
            model_name = models[int(time.time() * 100) % len(models)]
        prompt_text = self.build_prompt_text(prompt, response, conversation, model_name)

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

        messages = []
        if prompt.system is None:
            messages.append({"role": "system_default", "content": ""})
        if conversation:
            for resp in conversation.responses:
                if (
                    resp.prompt.prompt.strip(" ")
                    and resp.prompt.options.instruct != "completion"
                ):
                    if resp.prompt.system:
                        messages.append(
                            {"role": "system", "content": resp.prompt.system}
                        )
                    messages.append({"role": "user", "content": resp.prompt.prompt})
                    messages.append({"role": "assistant", "content": resp.text()})
                else:
                    messages.append({"role": "completion", "content": resp.text()})

        if prompt.prompt.strip(" ") == "" or instruct == "completion":
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
