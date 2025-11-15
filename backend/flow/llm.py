from langchain_openai import ChatOpenAI
from config import settings



MODEL_NAME = "gpt-4.1"

model = ChatOpenAI(
            model_name=MODEL_NAME, temperature=0, api_key=settings.OPENAI_API_KEY)

