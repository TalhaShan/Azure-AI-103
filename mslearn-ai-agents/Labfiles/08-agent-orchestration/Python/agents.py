import asyncio
import os
from typing import cast
from dotenv import load_dotenv

# Add references
# AgentResponseUpdate: the streamed pieces of text an agent produces
from agent_framework import AgentResponseUpdate
# FoundryChatClient: connects agents to a model deployed in your Foundry project
from agent_framework.foundry import FoundryChatClient
# SequentialBuilder: builds a workflow that runs agents one after another
from agent_framework.orchestrations import SequentialBuilder
# AzureCliCredential: uses your `az login` session to authenticate
from azure.identity import AzureCliCredential


load_dotenv()

async def main():
    # Agent instructions
    summarizer_instructions="""
    Summarize the customer's feedback in one short sentence. Keep it neutral and concise.
    Example output:
    App crashes during photo upload.
    User praises dark mode feature.
    """

    classifier_instructions="""
    Classify the feedback as one of the following: Positive, Negative, or Feature request.
    """

    action_instructions="""
    Based on the summary and classification, suggest the next action in one short sentence.
    Example output:
    Escalate as a high-priority bug for the mobile team.
    Log as positive feedback to share with design and marketing.
    Log as enhancement request for product backlog.
    """

    # Create the chat client
    # One client (project + model deployment) is shared by all three agents.
    # Values come from .env (PROJECT_ENDPOINT, MODEL_DEPLOYMENT_NAME).
    chat_client = FoundryChatClient(
        project_endpoint=os.getenv("PROJECT_ENDPOINT"),
        model=os.getenv("MODEL_DEPLOYMENT_NAME"),
        credential=AzureCliCredential(),
    )

    # Create agents
    # as_agent() turns the client into an agent with its own name and
    # instructions. Each agent has one narrow job.
    summarizer = chat_client.as_agent(
        instructions=summarizer_instructions,
        name="summarizer",
    )
    classifier = chat_client.as_agent(
        instructions=classifier_instructions,
        name="classifier",
    )
    action = chat_client.as_agent(
        instructions=action_instructions,
        name="action",
    )

    # Initialize the current feedback
    # The customer message that goes into the pipeline. Try your own text here.
    feedback = (
        "I use the dashboard every day and it works well, but the bright "
        "screen is tiring late at night. Please add a dark mode option."
    )

    # Build sequential orchestration
    # Agents run strictly in the order listed: summarizer -> classifier -> action.
    # By default each agent sees the whole conversation so far (the feedback plus
    # earlier answers), so "action" can use the summary and the classification.
    # Only the last agent's output is the final result by default, so we also
    # mark the first two as intermediate to see their answers too.
    workflow = SequentialBuilder(
        participants=[summarizer, classifier, action],
        intermediate_output_from=[summarizer, classifier],
    ).build()

    # Run and collect outputs
    # stream=True gives events while the agents are working. Each event carries
    # a small piece of text and the name of the agent that wrote it, so we
    # join the pieces per agent.
    outputs: dict[str, str] = {}
    async for event in workflow.run(f"Customer feedback: {feedback}", stream=True):
        if event.type in ("output", "intermediate") and isinstance(event.data, AgentResponseUpdate):
            update = event.data
            author = update.author_name or "assistant"
            outputs[author] = outputs.get(author, "") + (update.text or "")

    # Display outputs
    print(f"Customer feedback: {feedback}\n")
    for agent_name, text in outputs.items():
        print(f"[{agent_name}] {text.strip()}")


if __name__ == "__main__":
    asyncio.run(main())