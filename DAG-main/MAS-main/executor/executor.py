from agents.news_agent import NewsAgent
from agents.internet_agent import InternetAgent
from agents.fundamental_agent import FundamentalAgent
import json
AGENTS = {
    "news_agent": NewsAgent(),
    "internet_agent": InternetAgent(),
    "fundamental_agent": FundamentalAgent(),
}

def execute_plan(plan):
    results = {}

    for task in plan["tasks"]:
        agent_name = task["agent"]
        task_input = task["input"]

        if agent_name not in AGENTS:
            continue  # safety

        agent = AGENTS[agent_name]
        if(agent_name!="internet_agent"):
                try:
                    output= agent.run(task_input)
                except Exception as e:
                    print(f"Agent {agent_name} failed with exception: {e}, switching to Internet agent")
                    output=AGENTS["internet_agent"].run(task_input)
                    results[task["id"]] = {
                        "agent": "internet_agent",
                        "output": f"News Agent got failed had to run the Internet agent {output}",
                    }
                    continue
                
                # Check if output is a failure (either status "failed" or "failure")
                if(output.get("status") in ["failure", "failed"]):
                    print(f"Agent {agent_name} returned failure: {output.get('error', 'Unknown error')}, switching to Internet agent")
                    output=AGENTS["internet_agent"].run(task_input)
                    results[task["id"]] = {
                        "agent": "internet_agent",
                        "output": f"News Agent got failed had to run the Internet agent {output}",
                    }
                    continue
                
                # Success case - extract data
                results[task["id"]] = {
                    "agent": agent_name,
                    "output": output.get("data", output),  # Fallback to full output if no data key
                }
        else:
            output = agent.run(task_input)
            results[task["id"]] = {
                "agent": agent_name,
                "output": output,
            }
    with open("execution_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4)
    return results
                                                                                            