from langchain_openai import ChatOpenAI
from config import settings


MODEL_NAME = "gpt-3.5-turbo"

model = ChatOpenAI(
            model_name=MODEL_NAME, temperature=0, api_key=settings.OPENAI_API_KEY)

