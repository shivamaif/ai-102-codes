Use a custom function in an AI agent - agent.py code

import os
from dotenv import load_dotenv
from typing import Any
import json
import uuid
from pathlib import Path

from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition, FunctionTool
from openai.types.responses.response_input_param import (
    FunctionCallOutput,
    ResponseInputParam,
)

# Create a function to submit a support ticket
def submit_support_ticket(email_address: str, description: str) -> str:
    script_dir = Path(__file__).parent
    ticket_number = str(uuid.uuid4()).replace("-", "")[:6]
    file_name = f"ticket-{ticket_number}.txt"
    file_path = script_dir / file_name

    text = (
        f"Support ticket: {ticket_number}\n"
        f"Submitted by: {email_address}\n"
        f"Description:\n{description}"
    )
    file_path.write_text(text)

    return json.dumps(
        {"message": f"Support ticket {ticket_number} submitted. File saved as {file_name}"}
    )


def main():
    os.system("cls" if os.name == "nt" else "clear")

    load_dotenv()
    project_endpoint = os.getenv("PROJECT_ENDPOINT")
    model_deployment = os.getenv("MODEL_DEPLOYMENT_NAME")

    with (
        DefaultAzureCredential(
            exclude_environment_credential=True,
            exclude_managed_identity_credential=True,
        ) as credential,
        AIProjectClient(endpoint=project_endpoint, credential=credential) as project_client,
        project_client.get_openai_client() as openai_client,
    ):
        tool = FunctionTool(
            name="submit_support_ticket",
            parameters={
                "type": "object",
                "properties": {
                    "email_address": {
                        "type": "string",
                        "description": "The user's email address",
                    },
                    "description": {
                        "type": "string",
                        "description": "A description of the technical issue",
                    },
                },
                "required": ["email_address", "description"],
                "additionalProperties": False,
            },
            description="Submit a support ticket for a technical issue",
            strict=True,
        )

        agent = project_client.agents.create_version(
            agent_name="support-agent",
            definition=PromptAgentDefinition(
                model=model_deployment,
                instructions="""
You are a technical support agent.
When a user has a technical issue, you get their email address and a description.
Then submit a support ticket using the available function.
If a file is saved, tell the user the file name.
""",
                tools=[tool],
            ),
        )

        print(f"Using agent: {agent.name} (version: {agent.version})")

        conversation = openai_client.conversations.create()
        print(f"Created conversation (id: {conversation.id})")

        while True:
            user_prompt = input("Enter a prompt (or type 'quit' to exit): ")
            if user_prompt.lower() == "quit":
                break
            if not user_prompt.strip():
                print("Please enter a prompt.")
                continue

            openai_client.conversations.items.create(
                conversation_id=conversation.id,
                items=[{"type": "message", "role": "user", "content": user_prompt}],
            )

            response = openai_client.responses.create(
                conversation=conversation.id,
                extra_body={"agent": {"name": agent.name, "type": "agent_reference"}},
                input="",
            )

            if response.status == "failed":
                print(f"Response failed: {response.error}")
                continue

            input_list: ResponseInputParam = []

            for item in response.output:
                if item.type == "function_call" and item.name == "submit_support_ticket":
                    result = submit_support_ticket(**json.loads(item.arguments))

                    input_list.append(
                        FunctionCallOutput(
                            type="function_call_output",
                            call_id=item.call_id,
                            output=result,
                        )
                    )

            if input_list:
                response = openai_client.responses.create(
                    input=input_list,
                    previous_response_id=response.id,
                    extra_body={"agent": {"name": agent.name, "type": "agent_reference"}},
                )

            print(f"Agent response: {response.output_text}")

        openai_client.conversations.delete(conversation_id=conversation.id)
        print("Conversation deleted")

        project_client.agents.delete_version(
            agent_name=agent.name, agent_version=agent.version
        )
        print("Agent deleted")


if __name__ == "__main__":
    main()
