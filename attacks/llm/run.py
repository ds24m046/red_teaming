import tqdm
import json

from red_teaming.gym.src.servers.llm import OpenAIModel


DOTENV = "../.env"
CONFIG = "./attacks/llm/configs/baseline.json"
ATTACKS = "./attacks/llm/attacks.json"

llm = OpenAIModel(dotenv_path=DOTENV)

with open(CONFIG, "r") as f:
    config = json.load(f)

with open(ATTACKS, "r") as f:
    attacks = json.load(f)

responses = {}
for attack in tqdm.tqdm(attacks):
    
    name = attack["name"]
    prompt = attack["prompt"]
    
    llm.reset_messages()
    llm.add_message("system", config["system_prompt"])
    
    response = llm.call_model(message=prompt, include_history=True, validator=None)
    responses[name].append(response)

with open("responses.json", "w") as f:
    json.dump(responses, f, indent=4)
