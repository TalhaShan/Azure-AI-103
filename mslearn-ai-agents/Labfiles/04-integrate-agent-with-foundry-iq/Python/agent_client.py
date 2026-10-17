import os
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

# Load environment variables
# Reads PROJECT_ENDPOINT and AGENT_NAME from your .env file so no secrets or
# names are hard-coded in the script.
load_dotenv()
project_endpoint = os.getenv("PROJECT_ENDPOINT")
agent_name = os.getenv("AGENT_NAME")

# Validate configuration
# Fail early with a clear message if something is missing in .env.
if not project_endpoint or not agent_name:
    raise ValueError("PROJECT_ENDPOINT and AGENT_NAME must be set in .env file")

print(f"Connecting to project: {project_endpoint}")
print(f"Using agent: {agent_name}\n")

# Connect to the project and create a conversation

# 1. Create DefaultAzureCredential
# Uses your existing Azure sign-in (e.g. `az login`) to authenticate.
credential = DefaultAzureCredential()

# 2. Create AIProjectClient with endpoint
# The main client for your Foundry project (agents, connections, etc.).
project_client = AIProjectClient(endpoint=project_endpoint, credential=credential)

# 3. Get the OpenAI client
# An OpenAI-compatible client tied to your project. It provides the
# `conversations` and `responses` APIs used to chat with the agent.
openai_client = project_client.get_openai_client()

# 4. Get the agent by name
# Looks up the agent you built in the portal (product-expert-agent). This
# fails early if the name in .env is wrong, and gives us the exact name.
agent = project_client.agents.get(agent_name=agent_name)
print(f"Found agent: {agent.name}\n")

# 5. Create a new conversation
# The conversation lives in Foundry and stores every message and tool call,
# so the agent remembers earlier questions in this chat.
conversation = openai_client.conversations.create()
print(f"Conversation created (id: {conversation.id})\n")


# Conversation history for context (client-side tracking)
# Only used to print the history locally. The real history is stored in
# the Foundry conversation above.
conversation_history = []


def extract_citations(response):
    """
    Collect source references from a response.
    The Responses API attaches citations as "annotations" on the text parts
    of the message output (not as response.citations), so we walk through them.
    """
    sources = []
    for item in response.output:
        if getattr(item, "type", None) != "message":
            continue
        for part in getattr(item, "content", []):
            for annotation in getattr(part, "annotations", None) or []:
                title = getattr(annotation, "title", None)
                url = getattr(annotation, "url", None)
                label = title or url or "Knowledge Base"
                if label not in sources:  # avoid printing duplicates
                    sources.append(label)
    return sources


def send_message_to_agent(user_message):
    """
    Send a message to the agent and handle the response using the conversations API.
    """
    try:
        print("\nAgent: ", end="", flush=True)

        # Keep a local copy of what the user said (for the 'history' command)
        conversation_history.append({
            "role": "user",
            "content": user_message
        })

        # 1. Add the user message to the conversation using conversations.items.create()
        # This stores the message in the Foundry conversation.
        openai_client.conversations.items.create(
            conversation_id=conversation.id,
            items=[{"type": "message", "role": "user", "content": user_message}],
        )

        # 2. Create a response using responses.create() with agent reference
        # `conversation` gives the agent the full chat history. `agent_reference`
        # tells Foundry to answer using our agent (its model, instructions and
        # knowledge base tool) instead of a plain model. The message is already
        # in the conversation, so no extra input is needed.
        response = openai_client.responses.create(
            conversation=conversation.id,
            extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
            input=[],
        )

        # Report a failed run instead of silently showing nothing
        if response.status == "failed":
            print(f"Response failed: {response.error}\n")
            return None

        # 3. Extract the response text
        if response and response.output_text:
            response_text = response.output_text

            print(f"{response_text}\n")

            # 4. Check for citations if available
            # Citations come from the knowledge base search. Because of the
            # agent's instructions, markers like 【4:0†source】 may also appear
            # inside the text itself.
            sources = extract_citations(response)
            if sources:
                print("\nSources:")
                for source in sources:
                    print(f"  - {source}")

            # Store in conversation history (client-side)
            conversation_history.append({
                "role": "assistant",
                "content": response_text
            })

            return response_text
        else:
            print("No response received.\n")
            return None
    except Exception as e:
        # Covers errors such as 403 (permissions) or 429 (token rate limit)
        print(f"\n\nError: {str(e)}\n")
        return None


def display_conversation_history():
    """
    Display the full conversation history.
    """
    print("\n" + "="*60)
    print("CONVERSATION HISTORY")
    print("="*60 + "\n")

    for turn in conversation_history:
        role = turn["role"].upper()
        content = turn["content"]
        print(f"{role}: {content}\n")

    print("="*60 + "\n")


def main():
    """
    Main interaction loop.
    """
    print("Contoso Product Expert Agent")
    print("Ask questions about our outdoor and camping products.")
    print("Type 'history' to see conversation history, or 'quit' to exit.\n")

    while True:
        try:
            user_input = input("You: ").strip()

            # Ignore empty input
            if not user_input:
                continue

            # Exit command
            if user_input.lower() == 'quit':
                print("\nEnding conversation...")
                break

            # Show locally tracked history
            if user_input.lower() == 'history':
                display_conversation_history()
                continue

            # Send message and get response
            send_message_to_agent(user_input)

        except KeyboardInterrupt:
            # Ctrl+C exits cleanly
            print("\n\nInterrupted by user.")
            break
        except Exception as e:
            print(f"\nUnexpected error: {str(e)}\n")

    print("\nConversation ended.")


# Run main() only when this file is executed directly (python agent_chat.py)
if __name__ == "__main__":
    main()