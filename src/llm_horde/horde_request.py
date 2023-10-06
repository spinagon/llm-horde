#!/usr/bin/env python3

import time
import sys
import json
import importlib
import importlib.metadata
import re

import requests

ANON_APIKEY = "0" * 10
APIKEY = ANON_APIKEY
metadata = importlib.metadata.metadata("llm-horde")
name = metadata["Name"]
version = metadata["Version"]
url = metadata["Project-URL"]
CLIENT_AGENT = f"{name}:{version}:{url}"
JOB_MAX_TIME = 20 * 60
MODELS_CACHE = []


def get_headers():
    headers = {"apikey": APIKEY, "Client-Agent": CLIENT_AGENT}
    return headers


def templates():
    templates = json.loads(
        importlib.resources.files("llm_horde").joinpath("templates.json").read_text()
    )
    for template in templates.values():
        template["system_default"] = template["system"].format(
            content=template.get("system_default", "")
        )
    return templates


def get_instruct(mode, model_name):
    if mode != "auto":
        return mode
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
    for key, value in instruct_auto.items():
        if key.lower() in model_name.lower():
            return value
    return "alpaca"


def middle_out(prompt, length):
    start = prompt.rfind(" ", 0, length // 2)
    end = prompt.find("", len(prompt) - (length // 2), len(prompt))
    return prompt[:start] + prompt[end:]


def generate(prompt, models=[], options={}):
    params = {
        "max_context_length": 2048,
        "max_length": 240,
    }
    params.update(options)
    prompt = middle_out(prompt, params["max_context_length"] * 3)
    r = requests.post(
        "https://aihorde.net/api/v2/generate/text/async",
        headers=get_headers(),
        json={
            "prompt": prompt,
            "params": params,
            "models": models,
        },
    )

    try:
        id = r.json()["id"]
    except KeyError:
        print(r, r.json())
        return {"generations": [{"text": "Error"}]}

    start_time = time.time()
    while (time.time() - start_time) < JOB_MAX_TIME:
        time.sleep(3)
        r = requests.get(
            f"https://aihorde.net/api/v2/generate/text/status/{id}",
            headers=get_headers(),
        )
        if r.json()["done"]:
            return r.json()


def get_models():
    if MODELS_CACHE:
        return MODELS_CACHE
    r = requests.get(
        "https://aihorde.net/api/v2/workers?type=text", headers=get_headers()
    )
    try:
        data = r.json()
    except json.decoder.JSONDecodeError:
        print(r.text)
        return []
    models = {x["models"][0] for x in data}
    MODELS_CACHE[:] = sorted(models)
    return MODELS_CACHE


def match_model(pattern):
    return [
        model
        for model in get_models()
        if re.search(pattern, model, flags=re.IGNORECASE)
    ]


def build_conversation(messages, template):
    conversation = []
    template["completion"] = "{content}"
    for message in messages:
        role = message["role"]
        content = message["content"]
        conversation.append(template[role].format(content=content))
    return "".join(conversation)


if __name__ == "__main__":
    print(generate(sys.argv[1], [], {}))
