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