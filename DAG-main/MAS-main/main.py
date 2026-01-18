from router.planner import plan_tasks
from executor.executor import execute_plan
import json
from datetime import datetime
user_query = input("What financial news you want to know?: ")
from openai import OpenAI
import json
from datetime import datetime
client = OpenAI(api_key="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")
response = client.chat.completions.create(
        model="gpt-4o-mini",  # fast + cheap
        messages=[
            {"role": "system", "content": "You are a professional financial research analyst."},
            {"role": "user", "content": "I am just testing you"}
        ],
        temperature=0.2  # low hallucination
    )

SYSTEM_PROMPT = """
You are a professional financial research analyst.

Rules:
- Use ONLY the provided results.
- Do NOT hallucinate or add external facts.
- Be concise, factual, and structured.
- Focus on market impact, trends, and implications.
- If data is insufficient, clearly say so.
- Avoid motivational or generic statements.

Output a final financial report in markdown format with clear headings.
"""

def generate_final_report(user_query, results):
    user_prompt = f"""
    User Query:
    {user_query}

    Retrieved Financial News & Data:
    {json.dumps(results, indent=2, ensure_ascii=False)}

    Task:
    Generate a final financial intelligence report based strictly on the above data.
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",  # fast + cheap
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.2  # low hallucination
    )

    return response.choices[0].message.content

plan = plan_tasks(user_query)
results = execute_plan(plan)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
# print(results)
with open("output.json", "w", encoding="utf-8") as f:
    json.dump(
        {
            "query": user_query,
            "timestamp": timestamp,
            "results": results
        },
        f,
        indent=2,
        ensure_ascii=False
    )
final_report = generate_final_report(user_query, results)
with open(f"final_report_{timestamp}.md", "w", encoding="utf-8") as f:
    f.write(final_report)
print("Final Report Generated:\n")