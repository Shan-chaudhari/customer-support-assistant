from flask import Flask, render_template, request, jsonify
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
client = OpenAI()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    print("I received something!")

    data = request.get_json()
    print(data)
    message = data["message"]
    # NOTE: OpenAI responses call removed to avoid syntax error; placeholder kept
    print(message)
    completion = client.responses.create(
        model="gpt-5.5",
        input=message
    )

    return jsonify({
        "response": completion.output_text
    })

if __name__ == "__main__":
    app.run(debug=True)