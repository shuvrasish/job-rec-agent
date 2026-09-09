import os
from typing import Any

from dotenv import load_dotenv
from langchain_openrouter import ChatOpenRouter
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from agent.utils.tools import TOOLS
from agent.utils.models import JobAgentState

load_dotenv()


def build_llm_google() -> ChatGoogleGenerativeAI:
    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY is not set.")

    return ChatGoogleGenerativeAI(
        model=os.getenv("GOOGLE_MODEL", ""),
        thinking_level="medium",
        include_thoughts=False,
    )


def build_llm_openrouter() -> ChatOpenRouter:
    api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set.")

    return ChatOpenRouter(
        model=os.getenv("OPENROUTER_MODEL", ""),
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
   - years of experience: Take the user's first month and year of full time (not internship) work experience from the resume and pass it 
to extract_experience tool to get the total years and months of experience.
   - technical skills
   - programming languages
   - frameworks
   - databases
   - cloud technologies
   - current career level

3. Search for companies
   - Companies paying more than user's current salary for the same level of experience and skills
   - Base pay should be more than user's current base pay
   - It can be a startup or unicorn or a big company, but it should be a genuine company.

4. Search for jobs using search_jobs.

Search specifically for:

- Software Engineer
- SDE
- Backend Engineer
- Full-Stack Engineer

Locations:
- Hyderabad
- Bengaluru / Bangalore
- Remote (India)
- Remote (Global)

Experience:
- User's experience level -1 to + 3 years

Posted:
- within the last 7 days from today

5. When you find promising jobs, use crawl_job to verify the
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
- Job ID (if available)

6. Prefer direct company career pages over job aggregators.

7. Exclude:
- internships
- entry-level jobs requiring less than 3 years
- irrelevant roles
- inactive jobs
- duplicate jobs

8. Compare the verified jobs against the resume.

Give each job a match score from 0 to 100.
Give each job a difficulty score from 0 to 100 (if possible).

Only include jobs that are genuinely relevant.

9. Once you have enough verified jobs, send the complete
recommendations using send_email.

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

Do not expose private chain-of-thought or hidden reasoning.
Provide concise summaries of your actions when useful.
"""


def agent_node(state: JobAgentState):
    response = LLM_WITH_TOOLS.invoke(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            *state["messages"],
        ]
    )

    return {"messages": [response]}


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

def build_user_message(
    resume_path: str,
    to_email: str,
    additional_instructions: str = "",
) -> str:
    return f"""
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


def run_agent(
    resume_path: str,
    to_email: str,
    additional_instructions: str = "",
):
    """
    Normal non-streaming execution.

    Used by main.py / GitHub Actions / scheduled jobs.
    """

    return agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": build_user_message(
                        resume_path,
                        to_email,
                        additional_instructions,
                    ),
                }
            ]
        }
    )

def run_agent_streaming(
    resume_path: str,
    to_email: str,
    additional_instructions: str = "",
):
    user_message = build_user_message(
        resume_path,
        to_email,
        additional_instructions,
    )

    for chunk in agent.stream(
        {
            "messages": [
                {
                    "role": "user",
                    "content": user_message,
                }
            ]
        },
        stream_mode="updates",
    ):
        yield chunk