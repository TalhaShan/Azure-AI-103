from dotenv import load_dotenv
import os

# import namespaces
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
        print(f"Using agent: {agent.name}\n")
        
        
        # Get an OpenAI client
        # OpenAI-compatible client tied to your project. It provides the
        # conversations and responses APIs used to talk to the agent.
        openai_client = project_client.get_openai_client()

        # The conversation keeps the chat history in Foundry, so the agent
        # remembers earlier prompts in this session.
        conversation = openai_client.conversations.create()
        
        
        # Main loop
        while True:
            # Get user input
            prompt = input("User prompt (or 'quit'): ")
            if prompt == "quit" or len(prompt) == 0:
                break
            else:
                # Use the agent to get a response
                # Add the user's message to the conversation
                openai_client.conversations.items.create(
                    conversation_id=conversation.id,
                    items=[{"type": "message", "role": "user", "content": prompt}],
                )

                # Ask the agent to answer. agent_reference tells Foundry to use
                # our agent (its model, instructions and tools), not a bare model.
                response = openai_client.responses.create(
                    conversation=conversation.id,
                    extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
                    input=[],
                )

                # Show the answer, or the error if the run failed
                if response.status == "failed":
                    print(f"Response failed: {response.error}\n")
                else:
                    print(f"\nAgent: {response.output_text}\n")

        # Clean up: delete the conversation when the user quits
        openai_client.conversations.delete(conversation_id=conversation.id)
        print("Conversation deleted.")
                
    except Exception as ex:
        print(ex)

if __name__ == "__main__":
    main()