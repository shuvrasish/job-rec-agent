from langchain.agents.middleware import AgentState

class JobAgentState(AgentState):
    resume_path: str
    candidate_profile: str
    jobs: list
    recommendations: list