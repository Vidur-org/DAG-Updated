import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def openai_chat(
    messages,
    model="gpt-4o-mini",
    temperature=0.2,
    max_tokens=2048
):
    """Chat with OpenAI models"""
    res = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens
    )
    return res.choices[0].message.content

def openai_stream_chat(
    messages,
    model="gpt-4o-mini",
    temperature=0.3,
    max_tokens=2048
):
    """Streaming chat with OpenAI models"""
    stream = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True
    )
    
    for chunk in stream:
        if chunk.choices[0].delta.content is not None:
            yield chunk.choices[0].delta.content