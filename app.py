from openai import OpenAI
from dotenv import load_dotenv
from flask import Flask, render_template, request

load_dotenv() ## how to load api from env. file
convo_history = []
app = Flask(__name__) ## so python file nows its flask app
client = OpenAI() ## how to connect to open ai

def get_ai_response(user_question):

    with open("knowledge.txt", "r") as f:
        knowledge = f.read()
    
    with open("instructions.txt", "r") as f:
        instructions = f.read()

    prompt = f"Knowledge: {knowledge}\n\nInstructions: {instructions}"

    messages = [
        {"role": "system", "content": prompt},
        *convo_history,
        {"role": "user", "content": user_question}
    ]


    response = client.chat.completions.create( ## api documentation for chat completion
        model="gpt-3.5-turbo",
        messages = messages
    )
    convo_history.append({"role": "user", "content": user_question})

    convo_history.append({"role": "assistant", "content": response.choices[0].message.content})

    answer = response.choices[0].message.content

    return answer

@app.route("/")
def home():
    return "Hello World"

if __name__ == "__main__":
    app.run(debug=True)