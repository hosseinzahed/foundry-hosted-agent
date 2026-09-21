import os
import asyncio

import httpx
from agent_framework import Agent, SkillsProvider
from agent_framework.foundry import FoundryChatClient, ResponsesHostServer
from agent_framework.observability import configure_otel_providers
from azure.identity import DefaultAzureCredential, AzureDeveloperCliCredential
from dotenv import load_dotenv

from agent_framework.devui import serve

# Load environment variables from a .env file
load_dotenv(override=True)


def main():

    # Reads OTEL_EXPORTER_OTLP_* environment variables automatically
    configure_otel_providers()

    # Create a Foundry chat client instance
    foundry_client = FoundryChatClient(
        project_endpoint=os.getenv("FOUNDRY_PROJECT_ENDPOINT"),
        model=os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME"),
        credential=AzureDeveloperCliCredential()
    )

    # The SDK defaults (2 retries, 5s connect timeout) are too tight for transient
    # network/proxy resets, which surface as "APIConnectionError: Connection error."
    foundry_client.client.max_retries = 5
    foundry_client.client.timeout = httpx.Timeout(
        connect=30.0, read=600.0, write=600.0, pool=600.0)

    # Web IQ MCP tool
    web_iq_tool = foundry_client.get_mcp_tool(
        name="Web IQ MCP",
        url="https://api.microsoft.ai/v3/mcp",
        allowed_tools=["web", "news"],
        headers={"x-apikey": f"{os.getenv('WEB_IQ_API_KEY')}"},
        approval_mode="never_require"
    )

    # Web search tool
    web_search_tool = foundry_client.get_web_search_tool()

    # Get the code interpreter tool from the Foundry client
    code_interpreter_tool = foundry_client.get_code_interpreter_tool()

    # Set instructions for the agent
    instructions = """
    You're a helpful research assistant. Never answer from internal knowledge alone; 
    
    If the user asks for a research, always follow this process for every research task:
    1. Never answer from internal/pretrained knowledge, even if you believe you already know the answer. Always call the Web IQ MCP tool first to fetch current information from the web.
    2. Always use the Web IQ MCP tool to gather relevant, up-to-date information from the web.
    3. If needed, use the code interpreter tool to analyze, process, or transform the gathered data as needed.
    4. Combine the insights from both tools into a comprehensive, well-organized answer.
    5. Present the final results clearly and concisely, using headings or bullet points where helpful.
    6. Generate visualizations or summaries when they would aid understanding of the findings.
    7. Always cite your sources, listing the URLs or references used. If the Web IQ MCP tool returns no usable results, say so explicitly instead of filling gaps from memory.
    """

    # Create an agent instance
    agent = Agent(
        name="Researcher Agent",
        instructions="You're a helpful research assistant.",
        client=foundry_client,
        # tools=[web_search_tool, code_interpreter_tool],
        # History will be managed by the hosting infrastructure, thus there
        # is no need to store history by the service. Learn more at:
        # https://developers.openai.com/api/reference/resources/responses/methods/create
        default_options={"store": False},
    )

    # Run the DevUI server to interact with the agent locally
    serve(entities=[agent], port=8000, auto_open=True, auth_enabled=False)

    # Start the server for hosting responses (commented out for now)
    # server = ResponsesHostServer(agent)
    # server.run(port=8088)


if __name__ == "__main__":
    # Run it synchronously (local)
    main()

    # Run it asynchronously (hosted)
    # asyncio.run(main())


# Interacting with the agent
# Send a POST request to the server with a JSON body containing an "input" field to interact with the agent. For example:
# curl -X POST http://localhost:8088/responses -H "Content-Type: application/json" -d '{"input": "Hi"}'

# Multi-turn conversation
# To have a multi-turn conversation with the agent, include the previous response id in the request body. For example:
# curl -X POST http://localhost:8088/responses -H "Content-Type: application/json" -d '{"input": "How are you?", "previous_response_id": "REPLACE_WITH_PREVIOUS_RESPONSE_ID"}'
