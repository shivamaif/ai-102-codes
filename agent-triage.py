import os
from dotenv import load_dotenv

from azure.ai.agents import AgentsClient
from azure.ai.agents.models import (
    ConnectedAgentTool,
    MessageRole,
    ListSortOrder,
)
from azure.identity import DefaultAzureCredential

# Clear the console
os.system('cls' if os.name == 'nt' else 'clear')

# Load environment variables
load_dotenv()
project_endpoint = os.getenv("PROJECT_ENDPOINT")
model_deployment = os.getenv("MODEL_DEPLOYMENT_NAME")

# Connect to the agents client
agents_client = AgentsClient(
    endpoint=project_endpoint,
    credential=DefaultAzureCredential(
        exclude_environment_credential=True,
        exclude_managed_identity_credential=True
    ),
)

with agents_client:

    # ------------------ Priority Agent ------------------
    priority_agent = agents_client.create_agent(
        model=model_deployment,
        name="priority_agent",
        instructions="""
        Assess how urgent a ticket is based on its description.

        Respond with one of the following levels:
        - High: User-facing or blocking issues
        - Medium: Time-sensitive but not breaking anything
        - Low: Cosmetic or non-urgent tasks

        Only output the urgency level and a very brief explanation.
        """
    )

    # ------------------ Team Agent ------------------
    team_agent = agents_client.create_agent(
        model=model_deployment,
        name="team_agent",
        instructions="""
        Decide which team should own each ticket.

        Choose from:
        - Frontend
        - Backend
        - Infrastructure
        - Marketing

        Respond with the team name and a brief explanation.
        """
    )

    # ------------------ Effort Agent ------------------
    effort_agent = agents_client.create_agent(
        model=model_deployment,
        name="effort_agent",
        instructions="""
        Estimate how much work the ticket requires.

        Scale:
        - Small: 1 day
        - Medium: 2–3 days
        - Large: Multi-day or cross-team

        Respond with effort level and a brief justification.
        """
    )

    # ------------------ Connected Tools ------------------
    priority_tool = ConnectedAgentTool(
        id=priority_agent.id,
        name="priority_agent",
        description="Assess ticket urgency"
    )

    team_tool = ConnectedAgentTool(
        id=team_agent.id,
        name="team_agent",
        description="Assign ticket to team"
    )

    effort_tool = ConnectedAgentTool(
        id=effort_agent.id,
        name="effort_agent",
        description="Estimate ticket effort"
    )

    # ------------------ Triage Agent ------------------
    triage_agent = agents_client.create_agent(
        model=model_deployment,
        name="triage_agent",
        instructions="""
        Triage the ticket by determining priority, team ownership,
        and estimated effort using connected agents.
        """,
        tools=[
            priority_tool.definitions[0],
            team_tool.definitions[0],
            effort_tool.definitions[0],
        ]
    )

    # ------------------ Run the Workflow ------------------
    print("Creating agent thread...")
    thread = agents_client.threads.create()

    prompt = input("\nWhat's the support problem you need to resolve?: ")

    agents_client.messages.create(
        thread_id=thread.id,
        role=MessageRole.USER,
        content=prompt,
    )

    print("\nProcessing agent thread. Please wait...")
    run = agents_client.runs.create_and_process(
        thread_id=thread.id,
        agent_id=triage_agent.id
    )

    if run.status == "failed":
        print(f"Run failed: {run.last_error}")

    # ------------------ Output ------------------
    messages = agents_client.messages.list(
        thread_id=thread.id,
        order=ListSortOrder.ASCENDING
    )

    for message in messages:
        if message.text_messages:
            text = message.text_messages[-1].text.value
            print(f"{message.role}:\n{text}\n")

    # ------------------ Cleanup ------------------
    print("Cleaning up agents...")
    agents_client.delete_agent(triage_agent.id)
    agents_client.delete_agent(priority_agent.id)
    agents_client.delete_agent(team_agent.id)
    agents_client.delete_agent(effort_agent.id)

    print("All agents deleted.")
