from dotenv import load_dotenv
import os

# Import namespaces
# DefaultAzureCredential: signs in with your Azure login (e.g. `az login`)
from azure.identity import DefaultAzureCredential
# AIProjectClient: main client for your Foundry project
from azure.ai.projects import AIProjectClient


def main():
    try:
        # Clear the console
        os.system('cls' if os.name == 'nt' else 'clear')
        
        # Get Configuration Settings
        load_dotenv()
        foundry_endpoint = os.getenv('FOUNDRY_ENDPOINT')
        agent_name = os.getenv('AGENT_NAME')
        
        # Get project client
        # FOUNDRY_ENDPOINT must be the PROJECT endpoint, like
        # https://<resource>.services.ai.azure.com/api/projects/<project>
        credential = DefaultAzureCredential()
        project_client = AIProjectClient(endpoint=foundry_endpoint, credential=credential)
        
        # Look up the agent by name. This fails early if AGENT_NAME is wrong.
        agent = project_client.agents.get(agent_name=agent_name)
        print(f"Using agent: {agent.name}")
        
        # Get an OpenAI client
        # OpenAI-compatible client tied to your project. It provides the
        # conversations and responses APIs used to talk to the agent.
        openai_client = project_client.get_openai_client()

        # Use the agent to get a response
        # The conversation stores the chat history in Foundry, so the agent
        # remembers earlier messages.
        conversation = openai_client.conversations.create()

        while True:
            user_input = input("\nEnter a prompt (or 'quit' to exit): ").strip()
            if user_input.lower() == "quit":
                break
            if not user_input:
                continue

            # Add the user's message to the conversation
            openai_client.conversations.items.create(
                conversation_id=conversation.id,
                items=[{"type": "message", "role": "user", "content": user_input}],
            )

            # Ask the agent to respond. agent_reference tells Foundry to use
            # our agent (its model, instructions and tools), not a bare model.
            response = openai_client.responses.create(
                conversation=conversation.id,
                extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
                input=[],
            )

            # Report a failed run instead of printing nothing
            if response.status == "failed":
                print(f"Response failed: {response.error}")
                continue

            print(f"\nAgent: {response.output_text}")

        # Clean up: delete the conversation so nothing is left in the project
        openai_client.conversations.delete(conversation_id=conversation.id)
        print("Conversation deleted.")
        
    except Exception as ex:
        print(ex)

if __name__ == "__main__":
    main()