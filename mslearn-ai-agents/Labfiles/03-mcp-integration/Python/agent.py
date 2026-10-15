import os
from dotenv import load_dotenv

# Add references
# DefaultAzureCredential: authenticates using your Azure login (e.g. `az login`)
from azure.identity import DefaultAzureCredential
# AIProjectClient: main client for talking to an Azure AI Foundry project
from azure.ai.projects import AIProjectClient
# PromptAgentDefinition: describes the agent (model + instructions + tools)
# MCPTool: lets the agent call tools exposed by a remote MCP server
from azure.ai.projects.models import PromptAgentDefinition, MCPTool
# Types used to build the reply that approves/rejects an MCP tool call
from openai.types.responses.response_input_param import McpApprovalResponse, ResponseInputParam


# Load environment variables from .env file
load_dotenv()
project_endpoint = os.getenv("PROJECT_ENDPOINT")
model_deployment = os.getenv("MODEL_DEPLOYMENT_NAME")

# Connect to the agents client
# Using `with` ensures the credential and clients are closed automatically.
# The credential excludes env/managed-identity sources so it falls back to your
# local sign-in (Azure CLI / VS Code), which avoids slow credential probing.
with (
    DefaultAzureCredential(
        exclude_environment_credential=True,
        exclude_managed_identity_credential=True,
    ) as credential,
    AIProjectClient(endpoint=project_endpoint, credential=credential) as project_client,
    # OpenAI-compatible client used for conversations and responses
    project_client.get_openai_client() as openai_client,
):

    # Initialize agent MCP tool
    # server_label: a name we use to identify this MCP server later
    # server_url:   the remote MCP server (here: Azure REST API specs on GitHub)
    # require_approval="always": every tool call must be approved by us first
    mcp_tool = MCPTool(
        server_label="api-specs",
        server_url="https://gitmcp.io/Azure/azure-rest-api-specs",
        require_approval="always",
    )

    # Create a new agent with the MCP tool
    # create_version registers the agent (or a new version of it) in the project
    agent = project_client.agents.create_version(
        agent_name="MyAgent",
        definition=PromptAgentDefinition(
            model=model_deployment,
            instructions=(
                "You are a helpful agent that can use MCP tools to assist users. "
                "Use the available MCP tools to answer questions and perform tasks."
            ),
            tools=[mcp_tool],
        ),
    )
    print(f"Agent created (id: {agent.id}, name: {agent.name}, version: {agent.version})")

    # Create conversation thread
    # A conversation stores the message history so follow-up calls keep context
    conversation = openai_client.conversations.create()
    print(f"Created conversation (id: {conversation.id})")

    # Send initial request that will trigger the MCP tool
    # extra_body points the request at our agent instead of a bare model
    response = openai_client.responses.create(
        conversation=conversation.id,
        input="Please summarize the Azure REST API specifications Readme",
        extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
    )

    # Process any MCP approval requests that were generated
    # Because require_approval="always", the agent pauses and emits
    # "mcp_approval_request" items. We approve the ones from our trusted server.
    input_list: ResponseInputParam = []
    for item in response.output:
        if item.type == "mcp_approval_request":
            if item.server_label == "api-specs" and item.id:
                input_list.append(
                    McpApprovalResponse(
                        type="mcp_approval_response",
                        approve=True,  # set to False to reject the tool call
                        approval_request_id=item.id,
                    )
                )

    print("Final input:")
    print(input_list)

    # Send the approvals back, chained to the previous response so the agent
    # resumes where it paused, runs the MCP tool and produces the final answer
    response = openai_client.responses.create(
        input=input_list,
        previous_response_id=response.id,
        extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
    )
    print(f"\nAgent response: {response.output_text}")

    # Pause here so you can inspect the agent in the Foundry portal
    # (Agents section) before it gets deleted. Press Enter to continue.
    input("Press Enter to clean up")

    # Clean up resources by deleting the agent version
    # Prevents leaving unused agent versions behind in your project
    project_client.agents.delete_version(
        agent_name=agent.name,
        agent_version=agent.version,
    )
    print("Agent version deleted")