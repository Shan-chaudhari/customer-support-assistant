from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI()

response = client.responses.create(
    model="gpt-5.5",
    input="whos the best soccer player."
)

print(response.output_text)