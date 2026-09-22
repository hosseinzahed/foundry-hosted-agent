# Copyright (c) Microsoft. All rights reserved.

import os

from agent_framework import Agent, MCPStreamableHTTPTool
from agent_framework.foundry import FoundryChatClient, ResponsesHostServer
from azure.identity import DefaultAzureCredential, AzureDeveloperCliCredential
from agent_framework.observability import configure_otel_providers
from dotenv import load_dotenv
import httpx

# Load environment variables from .env file
load_dotenv(override=True)

# Configure OpenTelemetry providers for observability
configure_otel_providers()


def main():
    foundry_client = FoundryChatClient(
        project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
        model=os.environ["AZURE_AI_MODEL_DEPLOYMENT_NAME"],
        credential=DefaultAzureCredential(),        
        #credential=AzureDeveloperCliCredential()
    )
    
    # The SDK defaults (2 retries, 5s connect timeout) are too tight for transient
    # network/proxy resets, which surface as "APIConnectionError: Connection error."
    foundry_client.client.max_retries = 5
    foundry_client.client.timeout = httpx.Timeout(
        connect=30.0, read=600.0, write=600.0, pool=600.0)
    
    # Web IQ MCP tool
    web_iq_tool = MCPStreamableHTTPTool(
        name="Web IQ MCP",
        url="https://api.microsoft.ai/v3/mcp",
        allowed_tools=["web", "news"],
        http_client=httpx.AsyncClient(
            headers={"x-apikey": f"{os.getenv('WEB_IQ_API_KEY')}"},
            follow_redirects=False,
        ),
        approval_mode="never_require"
    )
    
    # Create the agent with the Web IQ MCP tool included
    agent = Agent(
        client=foundry_client,
        instructions="""
        You are a friendly assistant. 
        Use the web search tool when necessary. 
        Keep your answers brief. 
        Always provide citation links of your sources.
        """,        
        tools=[web_iq_tool],
        # History will be managed by the hosting infrastructure, thus there
        # is no need to store history by the service. Learn more at:
        # https://developers.openai.com/api/reference/resources/responses/methods/create
        default_options={"store": False},
    )

    # Start the responses host server to handle incoming requests
    server = ResponsesHostServer(agent)
    server.run()


if __name__ == "__main__":
    main()
