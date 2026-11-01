import os
import json
from dotenv import load_dotenv

# Add references
# DefaultAzureCredential: authenticates using your Azure login (e.g. `az login`)
from azure.identity import DefaultAzureCredential
# AIProjectClient: entry point for talking to an Azure AI Foundry project
from azure.ai.projects import AIProjectClient
# PromptAgentDefinition: describes the agent (model + instructions + tools)
# FunctionTool: declares a custom function the model is allowed to ask us to call
from azure.ai.projects.models import PromptAgentDefinition, FunctionTool
# Typed helpers for sending function results back to the model
from openai.types.responses.response_input_param import FunctionCallOutput, ResponseInputParam
# The actual Python implementations of our custom tools (see functions.py)
from functions import next_visible_event, calculate_observation_cost, generate_observation_report


def main():
    # Clear the console
    os.system('cls' if os.name == 'nt' else 'clear')

    # Load environment variables from .env file
    load_dotenv()
    project_endpoint = os.getenv("PROJECT_ENDPOINT")
    model_deployment = os.getenv("MODEL_DEPLOYMENT_NAME")

    # Connect to the project client
    # The `with` blocks make sure both clients are closed cleanly on exit.
    with (
        DefaultAzureCredential(
            exclude_environment_credential=True,
            exclude_managed_identity_credential=True,
        ) as credential,
        AIProjectClient(endpoint=project_endpoint, credential=credential) as project_client,
        # The OpenAI-compatible client is used for conversations and responses
        project_client.get_openai_client() as openai_client,
    ):

        # Define the event function tool
        # The JSON schema tells the model what arguments to supply when it calls the function.
        # strict=True requires every property to be listed in "required" and forbids extras.
        event_tool = FunctionTool(
            name="next_visible_event",
            description="Finds the next visible astronomical event for a given location.",
            parameters={
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The location to check, e.g. north_america, europe, asia, "
                                       "south_america, africa, australia, antarctica.",
                    }
                },
                "required": ["location"],
                "additionalProperties": False,
            },
            strict=True,
        )

        # Define the observation cost function tool
        cost_tool = FunctionTool(
            name="calculate_observation_cost",
            description="Calculates the cost of telescope observation time based on tier, hours and priority.",
            parameters={
                "type": "object",
                "properties": {
                    "telescope_tier": {
                        "type": "string",
                        "description": "Telescope tier: standard, advanced or premium.",
                    },
                    "hours": {
                        "type": "number",
                        "description": "Number of observation hours (must be greater than zero).",
                    },
                    "priority": {
                        "type": "string",
                        "description": "Booking priority: low, normal, high or urgent.",
                    },
                },
                "required": ["telescope_tier", "hours", "priority"],
                "additionalProperties": False,
            },
            strict=True,
        )

        # Define the observation report generation function tool
        report_tool = FunctionTool(
            name="generate_observation_report",
            description="Generates an observation session report and saves it to a text file.",
            parameters={
                "type": "object",
                "properties": {
                    "event_name": {"type": "string", "description": "Name of the astronomical event."},
                    "location": {"type": "string", "description": "Observation location."},
                    "telescope_tier": {"type": "string", "description": "Telescope tier: standard, advanced or premium."},
                    "hours": {"type": "number", "description": "Number of observation hours."},
                    "priority": {"type": "string", "description": "Booking priority: low, normal, high or urgent."},
                    "observer_name": {"type": "string", "description": "Name of the person observing."},
                },
                "required": ["event_name", "location", "telescope_tier", "hours", "priority", "observer_name"],
                "additionalProperties": False,
            },
            strict=True,
        )

        # Create a new agent with the function tools
        # create_version registers the agent in the project; the model only *requests*
        # function calls - our code below is what actually runs them.
        agent = project_client.agents.create_version(
            agent_name="astronomy-agent",
            definition=PromptAgentDefinition(
                model=model_deployment,
                instructions=(
                    "You are an astronomy observation assistant for Contoso Observatories. "
                    "Use the available functions to find upcoming astronomical events, "
                    "calculate telescope booking costs and generate observation reports. "
                    "If required details are missing, ask the user for them instead of guessing."
                ),
                tools=[event_tool, cost_tool, report_tool],
            ),
        )
        print(f"Created agent: {agent.name} (version {agent.version})")

        # Create a thread for the chat session
        # A conversation stores the message history server-side, so we don't resend it each turn.
        conversation = openai_client.conversations.create()

        # Tells the Responses API which agent should handle the request
        agent_ref = {"agent_reference": {"name": agent.name, "type": "agent_reference"}}

        # Map function names the model may request -> real Python functions
        available_functions = {
            "next_visible_event": next_visible_event,
            "calculate_observation_cost": calculate_observation_cost,
            "generate_observation_report": generate_observation_report,
        }

        while True:
            user_input = input("Enter a prompt for the astronomy agent. Use 'quit' to exit.\nUSER: ").strip()
            if user_input.lower() == "quit":
                print("Exiting chat.")
                break

            # Create a list to hold function call outputs that will be sent back as input to the agent
            input_list: ResponseInputParam = []

            # Send a prompt to the agent
            # Add the user's message to the conversation...
            openai_client.conversations.items.create(
                conversation_id=conversation.id,
                items=[{"type": "message", "role": "user", "content": user_input}],
            )
            # ...then ask the agent to respond to the conversation so far
            response = openai_client.responses.create(
                conversation=conversation.id,
                extra_body=agent_ref,
                input="",
            )

            # Retrieve the agent's response, which may include function calls
            if response.status == "failed":
                print(f"Response failed: {response.error}")
                continue

            # Process function calls
            # The output can contain several items; we only care about function_call items.
            for item in response.output:
                if item.type == "function_call":
                    func = available_functions.get(item.name)
                    if func is None:
                        result = json.dumps({"error": f"Unknown function '{item.name}'"})
                    else:
                        # Arguments arrive as a JSON string; parse and unpack into the function
                        args = json.loads(item.arguments)
                        print(f"[calling {item.name}({args})]")
                        result = func(**args)

                    # Pair the result with the call_id so the model knows which call it answers
                    input_list.append(
                        FunctionCallOutput(
                            type="function_call_output",
                            call_id=item.call_id,
                            output=result,
                        )
                    )

            # Send function call outputs back to the model and retrieve a response
            if input_list:
                # Pass the outputs into the SAME conversation (not previous_response_id), so the
                # stored history pairs every function_call with its function_call_output.
                # Otherwise the next prompt fails with "No tool output found for function call".
                response = openai_client.responses.create(
                    conversation=conversation.id,
                    input=input_list,
                    extra_body=agent_ref,
                )

            # Show the agent's final text answer
            print(f"\nAGENT: {response.output_text}\n")

        # Delete the agent when done
        # Cleans up the agent version we created so we don't leave resources behind.
        project_client.agents.delete_version(agent_name=agent.name, agent_version=agent.version)
        print("Deleted agent.")


if __name__ == '__main__':
    main()




# Event lookup: What is the next astronomical event visible from europe?
# It should call next_visible_event and answer with the Geminids Meteor Shower on 12-14, since today is October 11.
# Cost only: How much would 3 hours on a premium telescope cost at high priority?
# It should call calculate_observation_cost. The answer is $300 × 3 × 1.75 = $1,575.
# Full report: Generate an observation report for the Geminids Meteor Shower in europe. Premium telescope, 3 hours, high priority, observer name Talha.
# It should call generate_observation_report. The report file appears in the Python folder, named like report_geminids_meteor_shower_<date>_<time>.txt.
# Chained request: Find the next event for europe, then calculate the cost for 2 hours on an advanced telescope at normal priority.
# This shows the model requesting two functions in one go.
# Error handling: Cost for 5 hours on a deluxe telescope at high priority.
# There is no deluxe tier, so the function returns an error and the model should explain the valid options.
