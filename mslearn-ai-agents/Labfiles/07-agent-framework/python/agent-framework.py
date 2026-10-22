import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Add references
# Agent: the Microsoft Agent Framework class that runs the model + tools loop
# tool: decorator that turns a normal Python function into a tool the agent can call
from agent_framework import Agent, tool
# FoundryChatClient: connects the agent to a model deployed in your Foundry project
from agent_framework.foundry import FoundryChatClient
# AzureCliCredential: uses your `az login` session to authenticate
from azure.identity import AzureCliCredential
# Annotated + Field: describe each tool parameter so the model knows what to pass
from typing import Annotated
from pydantic import Field


load_dotenv()

async def main():
    # Clear the console
    os.system('cls' if os.name=='nt' else 'clear')

    # Load the expnses data file
    script_dir = Path(__file__).parent
    file_path = script_dir / 'data.txt'
    with file_path.open('r') as file:
        data = file.read() + "\n"

    # Ask for a prompt
    user_prompt = input(f"Here is the expenses data in your file:\n\n{data}\n\nWhat would you like me to do with it?\n\n")
    
    # Run the async agent code
    await process_expenses_data(user_prompt, data)
    
async def process_expenses_data(prompt, expenses_data):

    # Create a foundry chat client
    # Points at your Foundry project and the model deployment the agent will use.
    # Values come from .env (PROJECT_ENDPOINT, MODEL_DEPLOYMENT_NAME).
    chat_client = FoundryChatClient(
        project_endpoint=os.getenv("PROJECT_ENDPOINT"),
        model=os.getenv("MODEL_DEPLOYMENT_NAME"),
        credential=AzureCliCredential(),
    )

    # Initialize an agent with the tool and instructions
    # The agent runs in your Python process (nothing is saved in Foundry).
    # Instructions define its job; tools lists the functions it may call.
    agent = Agent(
        client=chat_client,
        name="expenses_agent",
        instructions="""You are an AI assistant for expense claims.
        When the user gives you expenses data and asks you to submit a claim,
        use the send_email function to send an email to expenses@contoso.com
        with the subject 'Expense Claim' and a body that contains the itemized
        expenses and the total. Then confirm to the user that you have done so.""",
        tools=send_email,
    )

    # Use the agent to process the expenses data
    # Combine the user's request with the file contents so the model sees both.
    # The agent decides if it needs to call send_email, runs it locally, and
    # then writes the final reply.
    response = await agent.run(f"{prompt}\n\nExpenses data:\n{expenses_data}")
    print(f"\n# Agent:\n{response}")


# Create a tool function for the email functionality
# @tool exposes the function to the agent. approval_mode="never_require" lets it
# run without asking for confirmation each time. The docstring and the Field
# descriptions are what the model reads to decide how to call it.
# This is a simulation: it prints the email instead of really sending one.
@tool(approval_mode="never_require")
def send_email(
    to: Annotated[str, Field(description="The recipient email address.")],
    subject: Annotated[str, Field(description="The subject line of the email.")],
    body: Annotated[str, Field(description="The body text of the email.")],
) -> str:
    """Send an email."""
    print("\nTo:", to)
    print("Subject:", subject)
    print(body, "\n")
    return "Email sent."


if __name__ == "__main__":
    asyncio.run(main())