"""
Multi-Agent Patterns Reference (Module 7.3)

This module demonstrates two fundamental multi-agent collaboration patterns
using Pydantic AI:

1. Agent-as-Tool Pattern: One agent invokes another as a tool
2. Agent Handoff Pattern: Complete control transfer between agents

These are reference implementations for learning purposes.
"""

import os
from dataclasses import dataclass
from typing import Union

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider


def _get_model():
    llm = os.getenv('LLM_CHOICE') or 'qwen2.5:7b-instruct-q4_K_M'
    base_url = os.getenv('LLM_BASE_URL') or 'https://api.openai.com/v1'
    api_key = os.getenv('LLM_API_KEY') or 'ollama'
    return OpenAIChatModel(llm, provider=OpenAIProvider(base_url=base_url, api_key=api_key))


# ═══════════════════════════════════════════════════════════════════════════════
# Pattern 1: Agent-as-Tool
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ResearchDeps:
    topic: str


@dataclass
class EmailDeps:
    recipient: str


# Email agent - a specialized agent for drafting emails
email_agent = Agent(
    _get_model(),
    system_prompt="You are an email drafting specialist. Write professional, concise emails.",
    deps_type=EmailDeps,
)


@email_agent.tool
async def send_email_draft(ctx: RunContext[EmailDeps], subject: str, body: str) -> str:
    """Tool to create an email draft."""
    return f"Draft created for {ctx.deps.recipient}:\nSubject: {subject}\nBody: {body}"


# Research agent - uses email_agent as a tool
research_agent = Agent(
    _get_model(),
    system_prompt="You are a research assistant. Research topics and compose emails when needed.",
    deps_type=ResearchDeps,
)


@research_agent.tool
async def compose_email(ctx: RunContext[ResearchDeps], recipient: str, subject: str, content: str) -> str:
    """
    Agent-as-Tool Pattern: The research agent invokes the email agent as a tool.
    Control returns to the research agent after the email agent completes.
    """
    email_deps = EmailDeps(recipient=recipient)
    result = await email_agent.run(
        f"Draft an email to {recipient} about {ctx.deps.topic}.\n"
        f"Subject: {subject}\nKey points: {content}",
        deps=email_deps,
    )
    return f"Email composed via sub-agent:\n{result.output}"


# ═══════════════════════════════════════════════════════════════════════════════
# Pattern 2: Agent Handoff
# ═══════════════════════════════════════════════════════════════════════════════

# In the handoff pattern, the research agent uses structured output to decide
# whether to respond directly or hand off to the email agent completely.

from pydantic import BaseModel


class DirectResponse(BaseModel):
    """Output when the research agent handles the query itself."""
    type: str = "direct"
    response: str


class EmailHandoff(BaseModel):
    """Output when control should transfer to the email agent."""
    type: str = "email_handoff"
    recipient: str
    subject: str
    content: str


# Research agent with handoff capability
handoff_research_agent = Agent(
    _get_model(),
    system_prompt="""
You are a research assistant. For research queries, respond directly.
For email requests, output an EmailHandoff with recipient, subject, and content.
""",
    deps_type=ResearchDeps,
    output_type=Union[DirectResponse, EmailHandoff],
)


async def run_with_handoff(query: str, topic: str) -> str:
    """
    Demonstrates the handoff pattern.

    If the research agent returns DirectResponse, we use it directly.
    If it returns EmailHandoff, we transfer control to the email agent.
    """
    deps = ResearchDeps(topic=topic)
    result = await handoff_research_agent.run(query, deps=deps)

    if isinstance(result.output, DirectResponse):
        return result.output.response

    elif isinstance(result.output, EmailHandoff):
        handoff = result.output
        # Control transfers completely to email agent
        email_deps = EmailDeps(recipient=handoff.recipient)
        email_result = await email_agent.run(
            f"Draft email to {handoff.recipient}\nSubject: {handoff.subject}\nContent: {handoff.content}",
            deps=email_deps,
        )
        return f"[Handed off to Email Agent]\n{email_result.output}"

    return str(result.output)


# ═══════════════════════════════════════════════════════════════════════════════
# Usage Examples
# ═══════════════════════════════════════════════════════════════════════════════

async def example_agent_as_tool():
    """Example: Research agent using email agent as a tool."""
    deps = ResearchDeps(topic="AI Agent Architectures")
    result = await research_agent.run(
        "Research AI agent architectures and draft an email summary to team@company.com",
        deps=deps,
    )
    return result.output


async def example_handoff():
    """Example: Research agent handing off to email agent."""
    return await run_with_handoff(
        "Send an email to team@company.com about the new routing architecture",
        topic="AI Agent Architectures",
    )
