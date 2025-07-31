from pipecat.services.groq.llm import GroqLLMService
from helpers.rag_searcher import get_search_response
import json
import os

class LLMService:
    def __init__(self, api_key: str, model: str):
        self.llm = GroqLLMService(
            api_key=api_key,
            model=model,
        )

    def get_llm(self):
        return self.llm
    
    def add_functions(self, functions):
        for function_name, function_handler in functions.items():
            self.llm.register_function(function_name, function_handler)

    async def azure_rag_search(self, query: str):
        """Perform a search using Azure RAG searcher."""
        args = {
            "query": query,
            "search_config": {
                "SEARCH_INDEX": "sfs-vector",
                "SEARCH_SEMANTIC_CONFIGURATION": "sfs-vector-semantic-configuration"
            }
        }
        return await get_search_response(args)

    def register_rag_search(self):
        """Register the Azure RAG search function with the LLM."""
        self.add_functions({"search": self.azure_rag_search})

    def register_functions_from_tools(self, tools_path = None) -> None:
        """Register functions dynamically based on tools.json."""
        print("Registering functions from tools.json")
        if not tools_path:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            default_tools_path = os.path.join(current_dir, "..", "helpers", "tools.json")
            tools_path = os.path.normpath(default_tools_path)
        print(f"Using tools.json from: {tools_path}")
        try:
            with open(tools_path, "r") as file:
                tools = json.load(file)

            function_map = {
                "search": self.azure_rag_search,
                # more mappings here if needed
            }

            for tool in tools:
                function_name = tool["name"]
                if function_name in function_map:
                    self.add_functions({function_name: function_map[function_name]})
            
            print("Functions registered successfully from tools.json")
        except Exception as e:
            raise Exception(f"Error registering functions from tools.json: {e}")

