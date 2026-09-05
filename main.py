<<<<<<< HEAD
"""Run the FastAPI service: ``python main.py``."""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=False)
=======
from agent import ask_agent


print("===================================")
print("       AI CAMPUS ASSISTANT")
print("===================================")
print("Type 'exit' to stop.")


while True:

    user_input = input("\nYou: ")

    if user_input.lower() == "exit":
        print("Goodbye!")
        break

    answer = ask_agent(user_input)

    print("\nAssistant:", answer)
>>>>>>> a4ba3ffd78a2334c89d1d74c49eb8148af132b8e
