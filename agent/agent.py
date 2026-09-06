from langchain_openrouter import ChatOpenRouter
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from agent.utils.tools import TOOLS
from dotenv import load_dotenv
from agent.utils.models import JobAgentState

import os

load_dotenv()  # Load environment variables from .env file

def build_llm_google() -> ChatGoogleGenerativeAI:
    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GOOGLE_API_KEY is not set. "
            "Add it to your .env file."
        )

    return ChatGoogleGenerativeAI(
        model=os.getenv(
            "GOOGLE_MODEL",
            "",
        ),
        thinking_level="medium",
        include_thoughts=True,
    )


def build_llm_openrouter() -> ChatOpenRouter:
    api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set. "
            "Add it to your .env file."
        )

    return ChatOpenRouter(
        model=os.getenv(
            "OPENROUTER_MODEL",
            "",
        ),
        api_key=api_key,
        temperature=0,
        max_retries=2,
    )


LLM = build_llm_google()

LLM_WITH_TOOLS = LLM.bind_tools(TOOLS)

TOOL_NODE = ToolNode(TOOLS)


SYSTEM_PROMPT = """
You are a job recommendation agent.

Your task is to find Software Engineering / SDE jobs that match
the user's resume.

You have access to tools for:
- reading the resume
- searching for jobs
- crawling job postings
- sending email

Follow this process:

1. Read the user's resume using read_resume.

2. Analyze the resume and understand:
   - years of experience
   - technical skills
   - programming languages
   - frameworks
   - databases
   - cloud technologies
   - current career level

3. Search for jobs using search_jobs.

Search specifically for:

- Software Engineer
- SDE
- SDE II
- MTS
- MTS II
- Senior Software Engineer
- Backend Engineer
- Full-Stack Engineer
- closely related software engineering roles

Locations:
- Hyderabad
- Bengaluru / Bangalore
- Remote (India)
- Remote (Global)

Experience:
- 3 – 6 years

Posted:
- within the last 7 days from today

4. When you find promising jobs, use crawl_job to verify the
actual job posting.

Verify:
- company
- job title
- location
- experience requirements
- date posted
- technologies / skills
- whether the job is still active
- job URL
- application URL
- Job ID

5. Prefer direct company career pages over job aggregators.

6. Exclude:
- internships
- entry-level jobs requiring less than 3 years
- jobs requiring substantially more than 5 years
- irrelevant roles
- inactive jobs
- duplicate jobs

7. Compare the verified jobs against the resume.

Give each job a match score from 0 to 100.

Only include jobs that are genuinely relevant.

8. Once you have enough verified jobs, send the complete recommendations using send_email.

The email should contain:

- A table containing all recommended jobs
- Company
- Job Title
- Location
- Experience Required
- Date Posted
- Key Technologies / Skills
- Match Score
- Why It Matches
- Job Link
- Application Link
- Job ID

Sort by Match Score from highest to lowest.

After the table include:

Top 5 Jobs
- One-line reason for each

Notable Gaps
- Important gaps between the resume and the strongest opportunities

Do not invent information.

If information cannot be verified, say "Not verified".

You should decide yourself which tools to call and when.
"""


def agent_node(state: JobAgentState):
    response = LLM_WITH_TOOLS.invoke(
        [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            *state["messages"],
        ]
    )

    return {
        "messages": [response]
    }


def should_continue(state: JobAgentState):
    last_message = state["messages"][-1]

    if last_message.tool_calls:
        return "tools"

    return END


graph = StateGraph(JobAgentState)

graph.add_node("llm", agent_node)
graph.add_node("tools", TOOL_NODE)

graph.add_edge(START, "llm")

graph.add_conditional_edges(
    "llm",
    should_continue,
    {
        "tools": "tools",
        END: END,
    },
)

graph.add_edge("tools", "llm")

agent = graph.compile()

def run_agent(
    resume_path: str,
    to_email: str,
    additional_instructions: str = "",
):
    user_message = f"""
        Run the job recommendation workflow.

        Resume path:
        {resume_path}

        Send the final email to:
        {to_email}

        Additional user instructions:
        {additional_instructions or "None"}

        Use the provided resume and follow the job search requirements
        from the system prompt.
    """

    return agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": user_message,
                }
            ]
        }
    )