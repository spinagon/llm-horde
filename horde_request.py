#!/usr/bin/env python3

import httpx
import time
import sys

def generate(prompt):
    r = httpx.post(
        "https://aihorde.net/api/v2/generate/text/async",
        headers={"apikey": "0" * 10, "Client-Agent": "llm-horde:0.1:spinagon"},
        json={
            "prompt": prompt,
            "params": {
                "max_context_length": 1024,
                "max_length": 120,
            },
            "models": [],
        },
    )

    id = r.json()["id"]

    for i in range(10):
        time.sleep(5)
        r = httpx.get(f"https://aihorde.net/api/v2/generate/text/status/{id}")
        if r.json()["done"]:
            return r.json()

if __name__ == '__main__':
    print(generate(sys.argv[1]))