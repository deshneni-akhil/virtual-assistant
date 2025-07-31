from openai.types.chat.chat_completion_system_message_param import ChatCompletionSystemMessageParam
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext

_system_message = (
    "You are a helpful assistant. "
    "You will be provided with a context that includes the user's previous messages. "
    "You should respond to the user's queries based on this context. "
    "If the context is not sufficient, you can ask the user for more information. "
    "Your responses should be concise and relevant to the user's queries. "
    "You should also maintain the context of the conversation to provide better responses in future interactions."
)

class OpenAILLMContextService:
    def __init__(self):
        self.__context = None

    def get_OpenAILLMcontext(self):
        self.__context = [
            ChatCompletionSystemMessageParam(
                role="system",
                content= _system_message
            )
        ]
        return OpenAILLMContext(messages=self.__context) # type: ignore

    def updateContext(self, content: str):
        if self.__context is not None:
            self.__context.append(
                ChatCompletionSystemMessageParam(
                    role = 'system',
                    content = content
                )
            )
