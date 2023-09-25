# llm-horde
[LLM](https://llm.datasette.io/) plugin for models hosted by [AI Horde](https://aihorde.net/)

## Installation

First, [install the LLM command-line utility](https://llm.datasette.io/en/stable/setup.html).

Now install this plugin in the same environment as LLM.
```bash
llm install https://github.com/spinagon/llm-horde/archive/refs/heads/main.zip
```

## Configuration

First [Register an account](https://aihorde.net/register) which will generate for you an API key. Store that key somewhere.

 - If you do not want to register, you can use '0000000000' as api_key to connect anonymously. If you don't set your key, it will be used automatically. However anonymous accounts have the lowest priority when there's too many concurrent requests!
 - To increase your priority you will need a unique API key and then to increase your Kudos. [Read how Kudos are working](https://dbzer0.com/blog/the-kudos-based-economy-for-the-koboldai-horde/).

You can set that as an environment variable called `AIHORDE_KEY`, or add it to the `llm` set of saved keys using:

```bash
llm keys set aihorde
```
```
Enter key: <paste key here>
```

## Usage

To list available models, run:
```bash
llm models list
```
You should see a list that looks something like this:
```
AI Horde: horde/Henk717/airochronos-33B
AI Horde: horde/tgi-fp16-8k/migtissera/Synthia-70B-v1.2b
AI Horde: horde/Gryphe/MythoMax-L2-13b
```
To run a prompt against a model, pass its full model ID to the `-m` option, like this:
```bash
llm -m horde/tgi-fp16-8k/migtissera/Synthia-70B-v1.2b "Five spooky names for a pet vampire bat"
```
You can set a shorter alias for a model using the `llm aliases` command like so:
```bash
llm aliases set synthia horde/tgi-fp16-8k/migtissera/Synthia-70B-v1.2b
```
Now you can prompt it using:
```bash
cat llm_horde.py | llm -m synthia -s 'write some pytest tests for this'
```
If you use "horde" as a model name, you can select one or more models matching a regex pattern using "pattern" option:
```bash
llm -m horde -o pattern "13B" "What is the capital of Lebanon?"
```
You can change the maximum length of returned text by using "max_tokens" option (80 by default), most workers will not :
```bash
llm -m horde -o pattern mythomax -s 'Write a sonnet' -o max_tokens 120
```
If you want to continue generating text without new prompt, try:
```bash
llm -c ""
```
To start interactive chat, type 
```bash
llm chat -m horde -o pattern llama2
```
