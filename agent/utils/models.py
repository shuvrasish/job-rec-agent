from langchain.agents.middleware import AgentState
from datetime import datetime

from langchain.agents.middleware import AgentState
from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SentJob(Base):
    __tablename__ = "sent_jobs"

    user_email: Mapped[str] = mapped_column(
        String(320),
        primary_key=True,
    )

    job_id: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
    )

    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

class JobAgentState(AgentState):
    resume_path: str
    candidate_profile: str
    jobs: list
    recommendations: list
    
