#!/usr/bin/env python3

import httpx
import time
import sys

APIKEY = "0" * 10
CLIENT_AGENT = "llm-horde:0.1:https://github.com/spinagon"


def get_headers():
    headers = {"apikey": APIKEY, "Client-Agent": CLIENT_AGENT}
    return headers


def generate(prompt, options):
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
            "models": [],
        },
    )

    try:
        id = r.json()["id"]
    except KeyError:
        print(r, r.json())
        return {"generations": [{"text": "Error"}]}

    for i in range(10):
        time.sleep(5)
        r = httpx.get(
            f"https://aihorde.net/api/v2/generate/text/status/{id}",
            headers=get_headers(),
        )
        if r.json()["done"]:
            return r.json()


def get_models():
    r = httpx.get("https://aihorde.net/api/v2/workers?type=text", headers=get_headers())
    models = {x["models"][0] for x in r.json()}
    return list(models)


if __name__ == "__main__":
    print(generate(sys.argv[1]))
