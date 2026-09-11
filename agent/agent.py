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
You are a job recommendation agent that finds Software Engineering /
SDE jobs matching the user's resume and emails the best verified jobs.

You have access to tools for:
- reading the resume (read_resume)
- extracting experience (extract_experience)
- searching for jobs (search_jobs)
- crawling job postings (crawl_job)
- filter out jobs for which email has already been sent (filter_unsent_jobs)
- sending email (send_email)
Process:

1. Read the resume with read_resume.

2. Analyze:
   - full-time experience (exclude internships)
   - skills, languages, frameworks, databases, cloud
   - current career level

   Use extract_experience with the first month/year of full-time
   employment from the resume.

3. Search for:
   - Software Engineer
   - SDE
   - Backend Engineer
   - Full-Stack Engineer

   Use the locations and experience range given by the user.
   Prefer jobs posted within the last 7 days.

4. Prefer:
   - strong resume matches
   - product-based companies
   - direct company career pages
   - jobs meeting the user's compensation requirements

5. Verify promising jobs with crawl_job.

   Verify company, title, location, experience, posting date,
   active status, application URL, and job posting URL.

6. Job ID:
   - The job posting URL is the Job ID.
   - Use the canonical job posting URL as the unique identifier.
   - Do not invent or modify Job IDs.
   - The same job posting URL always represents the same job.
   - Normalize obvious URL differences such as a trailing slash when
     determining whether two jobs are duplicates.

7. Exclude:
   - internships
   - clearly unsuitable seniority
   - irrelevant jobs
   - inactive jobs
   - duplicates
   - jobs without a verified job posting URL
   - jobs already sent to the user

8. Before sending:
   - deduplicate by Job ID (job posting URL)
   - call filter_unsent_jobs with the user's email and all
     recommended Job IDs
   - remove every filtered-out job

9. Give each final job a Match Score (0-100) and Difficulty Score
   (0-100, when possible).

10. Call send_email only with the final jobs.
    The job_ids argument MUST contain exactly the job posting URLs
    included in the email.

Email format:
- table with Company, Job Title, Location, Experience Required,
  Date Posted, Key Technologies, Match Score, Difficulty Score,
  Why It Matches, Job Link/Job Id
- sort by Match Score descending
- include Top 5 Jobs with one-line reasons
- include Notable Gaps

For Job ID, use the verified job posting URL.

Do not invent information. Use "Not verified" when necessary.
Do not expose chain-of-thought.
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