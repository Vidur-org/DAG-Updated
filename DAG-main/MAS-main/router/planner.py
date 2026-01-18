import json
from llm.llm_client import call_llm
from prompts.router_prompt import ROUTER_PROMPT
from datetime import datetime

def plan_tasks(user_query):
    response = call_llm(
        system=ROUTER_PROMPT+"Keep in mind today's date is "+datetime.now().strftime("%Y-%m-%d"),
        user=user_query
    )
    print("Planner Response:", response)
    return json.loads(response)