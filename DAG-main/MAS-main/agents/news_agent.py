from typing import Dict, Any, List
from agents.base import Agent
from llm.llm_client import call_llm, call_llm_json
from tools.news_search import News_Search
from prompts.preprocess_prompt import PREPROCESS_PROMPT
from typing import TypedDict

def success(data, confidence=0.7, citations=None):
    return {"status": "success", "confidence": confidence, "data": data, "citations": citations or []}

def failure(reason):
    return {"status": "failed", "error": reason}
class NewsResult(TypedDict):
    title: str
    date: str
    source: str
    content: str
class NewsAgent(Agent):
    def __init__(self):
        super().__init__("NewsAgent")

    def preprocess(self, task_input: str) -> Dict[str, Any]:
        """
        Converts user query into:
        {
            "START_DATE": "YYYY-MM-DD",
            "END_DATE": "YYYY-MM-DD",
            "QUERY": str,
            "TOP_K": int
        }
        """
        return call_llm_json(
            system=PREPROCESS_PROMPT,
            user=task_input
        )

    def call_tool(self, processed_input: Dict[str, Any]) -> List[NewsResult]:
        print("Processed Input:", processed_input)
        
        news_response,top_score=News_Search(
            query=processed_input["QUERY"],
            start_date=processed_input["START_DATE"],
            end_date=processed_input["END_DATE"],
            top_k=10
        )
        
        print(f"📊 News Search Results: {len(news_response)} articles, top score: {top_score:.4f}")
        
        if(len(news_response)==0):
            return failure(f"No news articles found for '{processed_input['QUERY']}' between {processed_input['START_DATE']} and {processed_input['END_DATE']}")
        
        if(top_score<0.4):
            return failure(f"News relevance too low (score: {top_score:.4f}). Found articles but they don't match '{processed_input['QUERY']}' well enough.")

        citations = []
        for item in news_response:
            citations.append({
                "source": "news",
                "title": item.get("title", "N/A"),
                "url": item.get("url", "N/A"),
                "date": item.get("publish_date", ""),
                "query": processed_input.get("QUERY", "")
            })

        return success(news_response, citations=citations)

    def postprocess(self, tool_output: List[NewsResult],task_input) -> str:
        """
        Convert structured news results → final answer
        """
        # if(tool_output is None or len(tool_output)==0 or ):
        #     return "There is not any significant relevant news available to answer the query."
        formatted_news = ""
        print("Tool Output:", tool_output)
        if(tool_output["status"]=="success"):
            print("Tool Output Data:", tool_output["data"])
            for output in tool_output["data"]: 
                formatted_news += "".join(
                f"Title: {output['title']}\n"
                f"Date: {output['publish_date']}\n"
                # f"Source: {output['url']}\n"
                f"Summary: {output['summary']}"
            )
            print("Formatted News:", formatted_news)
            user_prompt="""There are the news articles needed for context to answer:
            {}
            
            Based on these articles as context write a answer for this query with given system instruction:
            query:
            {}
            """.format(formatted_news,task_input)
            llm_response=call_llm(
                system="Answer based on query asked and given the news articles. Don't write extra words like this is the answer for the query want straight answer in string. Also take care just don't write 1 line answer I want explnation also why was your answer take help of context to get the answer",
                user=user_prompt
            )
            citations = tool_output.get("citations", [])
            return  success(llm_response+"\n\n\nBased on the artciles\n\n"+formatted_news, citations=citations)
        else:
            error_msg = tool_output.get("error", "Unknown error")
            return failure(f"News agent failed: {error_msg}")
    def run(self, task_input: str) -> str:
        processed_input = self.preprocess(task_input)
        tool_output = self.call_tool(processed_input)
        return self.postprocess(tool_output,task_input)
