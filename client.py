MCP Demo

import os
from dotenv import load_dotenv

from azure.identity import DefaultAzureCredential
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import McpTool, ToolSet, ListSortOrder

# --------------------------------------------------
# Load environment variables
# --------------------------------------------------
load_dotenv()

project_endpoint = os.getenv("PROJECT_ENDPOINT")
model_deployment = os.getenv("MODEL_DEPLOYMENT_NAME")

if not project_endpoint or not model_deployment:
    raise ValueError("PROJECT_ENDPOINT or MODEL_DEPLOYMENT_NAME not set")

# --------------------------------------------------
# Create Agents client
# --------------------------------------------------
agents_client = AgentsClient(
    endpoint=project_endpoint,
    credential=DefaultAzureCredential(
        exclude_environment_credential=True,
        exclude_managed_identity_credential=True,
    ),
)

# --------------------------------------------------
# MCP server configuration
# --------------------------------------------------
mcp_server_url = "https://learn.microsoft.com/api/mcp"
mcp_server_label = "mslearn"

mcp_tool = McpTool(
    server_label=mcp_server_label,
    server_url=mcp_server_url,
)

# Disable approval prompts
mcp_tool.set_approval_mode("never")

toolset = ToolSet()
toolset.add(mcp_tool)

# --------------------------------------------------
# Main execution
# --------------------------------------------------
with agents_client:
    # Create agent
    agent = agents_client.create_agent(
        model=model_deployment,
        name="my-mcp-agent",
        instructions="""
You have access to an MCP server called `microsoft.docs.mcp`.
Use it to search Microsoft's latest official documentation
to answer questions accurately.
""",
    )

    print(f"Created agent, ID: {agent.id}")
    print(f"MCP Server: {mcp_tool.server_label} at {mcp_tool.server_url}")

    # Create a conversation thread
    thread = agents_client.threads.create()
    print(f"Created thread, ID: {thread.id}")

    # Get user input
    prompt = input("\nHow can I help?: ")

    # Add user message
    message = agents_client.messages.create(
        thread_id=thread.id,
        role="user",
        content=prompt,
    )
    print(f"Created message, ID: {message.id}")

    # Create and process run
    run = agents_client.runs.create_and_process(
        thread_id=thread.id,
        agent_id=agent.id,
        toolset=toolset,
    )

    print(f"Created run, ID: {run.id}")
    print(f"Run completed with status: {run.status}")

    if run.status == "failed":
        print(f"Run failed: {run.last_error}")

    # --------------------------------------------------
    # Display run steps
    # --------------------------------------------------
    run_steps = agents_client.run_steps.list(
        thread_id=thread.id,
        run_id=run.id,
    )

    for step in run_steps:
        print(f"Step {step['id']} status: {step['status']}")

        details = step.get("step_details", {})
        tool_calls = details.get("tool_calls", [])

        if tool_calls:
            print("  MCP Tool calls:")
            for call in tool_calls:
                print(f"    Tool Call ID: {call.get('id')}")
                print(f"    Name: {call.get('name')}")
                print(f"    Type: {call.get('type')}")

        print()

    # --------------------------------------------------
    # Print conversation
    # --------------------------------------------------
    messages = agents_client.messages.list(
        thread_id=thread.id,
        order=ListSortOrder.ASCENDING,
    )

    print("\nConversation:")
    print("-" * 50)
    for msg in messages:
        if msg.text_messages:
            print(f"{msg.role.upper()}: {msg.text_messages[-1].text.value}")
            print("-" * 50)

    # --------------------------------------------------
    # Cleanup
    # --------------------------------------------------
    agents_client.delete_agent(agent.id)
    print("Deleted agent")
