#!/usr/bin/env python3

import httpx
import time
import sys
import json

ANON_APIKEY = "0" * 10
APIKEY = ANON_APIKEY
CLIENT_AGENT = "llm-horde:0.1:https://github.com/spinagon"
JOB_MAX_TIME = 20 * 60


def get_headers():
    headers = {"apikey": APIKEY, "Client-Agent": CLIENT_AGENT}
    return headers


def generate(prompt, models, options):
    params = {
        "max_context_length": 1024,
        "max_length": 80,
    }
    params.update(options)
    r = httpx.post(
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
        r = httpx.get(
            f"https://aihorde.net/api/v2/generate/text/status/{id}",
            headers=get_headers(),
        )
        if r.json()["done"]:
            return r.json()


def get_models():
    r = httpx.get("https://aihorde.net/api/v2/workers?type=text", headers=get_headers())
    try:
        data = r.json()
    except json.decoder.JSONDecodeError:
        print(r.text)
        return []
    models = {x["models"][0] for x in data}
    return list(models)


if __name__ == "__main__":
    print(generate(sys.argv[1], [], {}))
