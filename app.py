from openai import OpenAI
from dotenv import load_dotenv

load_dotenv() ## how to load api from env. file

client = OpenAI() ## how to connect to open ai
user_question = ""
while user_question != "exit":
    user_question = input("Please enter your question: ")
    with open("knowledge.txt", "r") as f:
        knowledge = f.read()

    prompt = f"Answer the following question based on the knowledge provided:\n\nKnowledge: {knowledge}\n\nQuestion: {user_question}"

    response = client.chat.completions.create( ## api documentation for chat completion
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    if user_question.lower() == "exit":
        break
    print(response.choices[0].message.content)