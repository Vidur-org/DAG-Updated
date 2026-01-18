from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Optional, Literal
from config import CONFIG


NODE_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "reasoning": {
            "type": "string",
            "description": "Reasoning for generating child questions"
        },
        "child_node_prompts": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "List of child questions"
        },
        "internet_search": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "Search queries to fetch external context"
        }
    },
    "required": [
        "reasoning",
        "child_node_prompts",
        "internet_search"
    ],
    "additionalProperties": False
}



ANSWER_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {
            "type": "string",
            "description": "The final answer to the question"
        },
        "reasoning": {
            "type": "string",
            "description": "Reasoning behind the answer"
        }
    },
    "required": [
        "answer",
        "reasoning"
    ],
    "additionalProperties": False
}



FINAL_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "position": {
            "type": "string",
            "enum": ["long", "short", "neutral"],
            "description": "Final investment position"
        },
        "detailed_analysis": {
            "type": "string",
            "description": "Detailed analysis supporting the decision"
        },
        "confidence_level": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "Confidence level between 0 and 1"
        }
    },
    "required": [
        "position",
        "detailed_analysis",
        "confidence_level"
    ],
    "additionalProperties": False
}




def get_child_question_prompt(
    stock: str,
    context: str,
    question: str,
    max_children: int,
    isleaf: bool = False,
    level: int = 0,
    additional_context: str = ""
) -> str:

    if isleaf:
        return f"""
        You are analyzing a financial investment question for the stock/instrument {stock}.
        You are at a LEAF node in the reasoning tree, for investment analysis.
        You are analyzing a financial investment question for {stock}.

        Parent Question:
        {question}

        Available Context:
        {context}

        Task:
        This is a LEAF node. Answer the parent question clearly and concisely.
        Return an empty array for "child_node_prompts"
        Explain briefly why no further decomposition is needed.

        The ansewer should:
        - Focus on a different analytical angle
        - Be specific and actionable
        - Reflect the investment horizon
        - You can do some guess estimates to fill gaps if needed, but make sure to do a sanity check.
        - Have a predictive tone, also criticise some reports if needed, you are the expert, show me something that cannot be found easily elsewhere.
        - numerical grounding where possible, very important for investment analysis.
        """

    return f"""
        You are analyzing a financial investment question for the stock/instrument {stock} for an investment horizon of {CONFIG['INVESTMENT_WINDOW']}.
        You are at an INTERNAL node in the reasoning tree, for investment analysis, at level {level} in a tree of maximum {CONFIG['MAX_LEVELS']} levels, and need to generate child prompts.
        Reference the following additional context for company and time details at every node:
        {additional_context}

        Each child prompt should help break down the parent question into manageable parts. Make sure the child prompts are:
        - Specific
        - Actionable
        - Diverse
        - Mutually exclusive (no overlap)
        - Unique (do not repeat or cover the same ground)
        - As clearly defined as possible
        - Together comprehensive
        The child prompt must be detailed (around 50 words) to set a clear analysis direction. The child questions must be such that answering them will help answer the parent question, because the answers will be provided to you later.
        For example, if the parent question is "Perform a DCF valuation", the child questions could be "What are the revenue growth assumptions?", "What is the discount rate (WACC) to be used?", etc.

        Parent Question:
        {question}

        Available Context:
        {context}

        Task:
        1. Generate exactly {max_children} child questions that decompose the parent question. Each child question MUST be unique, non-overlapping, and as clearly defined as possible.
        2. Generate 2-4 internet search queries to fetch missing context. The internet search queries should be specific and yet diverse to the child questions you generated.

        Each question should:
        - Focus on a different analytical angle
        - Be specific and actionable
        - Reflect the investment horizon
        - You can do some guess estimates to fill gaps if needed, but make sure to do a sanity check.
        - Have a predictive tone, also criticise some reports if needed, you are the expert, show me something that cannot be found easily elsewhere.
        - Numerical grounding where possible, very important for investment analysis.

        Return format:
        {{
        "reasoning": "Brief explanation of your approach",
        "child_node_prompts": ["question 1", "question 2", ...],
        "internet_search": ["search query 1", "search query 2", ...]
        }}
        """


def get_answer_prompt(parent_question: str, all_child_answers: str, all_child_questions: str) -> str:
    if all_child_answers:
        return f"""
        Parent Question:
        {parent_question}

        Child Questions:
        {all_child_questions}

        Child Answers:
        {all_child_answers}

        Task:
        Synthesize the child answers into a single, decisive response.
        Be blunt, numerically grounded, and explicit about assumptions.
        You can do some guess estimates to fill gaps if needed, but make sure to do a sanity check.
        Have a predictive tone, also criticise some reports if needed, you are the expert, show me something that cannot be found easily elsewhere.

        The ansewer should:
        - Focus on a different analytical angle
        - Be specific and actionable
        - Reflect the investment horizon
        - You can do some guess estimates to fill gaps if needed, but make sure to do a sanity check.
        - Have a predictive tone, also criticise some reports if needed, you are the expert, show me something that cannot be found easily elsewhere.
        - numerical grounding where possible, very important for investment analysis.
        """

    return f"""
        Question:
        {parent_question}

        Task:
        Provide a decisive investment recommendation with numerical justification.
        Be blunt and avoid hedging.
        """

def get_final_response_prompt(synthesis_prompt: str) -> str:
    return f"""
        You are to provide a final investment decision based on the following synthesis:
        {synthesis_prompt}
        Task:
        Decide on a position: long, short, or neutral.
        Justify your decision with detailed analysis and a confidence level (0.0 to 1.0).

        The ansewer should:
        - Focus on a different analytical angle
        - Be specific and actionable
        - Reflect the investment horizon
        - You can do some guess estimates to fill gaps if needed, but make sure to do a sanity check.
        - Have a predictive tone, also criticise some reports if needed, you are the expert, show me something that cannot be found easily elsewhere.
        - numerical grounding where possible, very important for investment analysis.
        """
