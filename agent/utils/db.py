import os
from contextlib import contextmanager

from dotenv import load_dotenv
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import insert

from agent.utils.models import Base, SentJob

load_dotenv()


POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")

required = {
    "POSTGRES_HOST": POSTGRES_HOST,
    "POSTGRES_DB": POSTGRES_DB,
    "POSTGRES_USER": POSTGRES_USER,
    "POSTGRES_PASSWORD": POSTGRES_PASSWORD,
}

missing = [key for key, value in required.items() if not value]

if missing:
    raise RuntimeError(
        f"Missing PostgreSQL environment variables: {', '.join(missing)}"
    )


DATABASE_URL = (
    f"postgresql+psycopg://"
    f"{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}"
    f"/{POSTGRES_DB}"
    f"?sslmode=require"
)


engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    expire_on_commit=False,
)


def init_db() -> None:
    Base.metadata.create_all(engine)


@contextmanager
def get_db():
    db = SessionLocal()

    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_sent_job_ids(user_email: str) -> set[str]:
    user_email = user_email.strip().lower()

    with get_db() as db:
        rows = (
            db.query(SentJob.job_id)
            .filter(SentJob.user_email == user_email)
            .all()
        )

        return {row[0] for row in rows}


def record_sent_jobs(
    user_email: str,
    job_ids: list[str],
) -> None:
    user_email = user_email.strip().lower()
    if not job_ids:
        return

    values = [
        {
            "user_email": user_email,
            "job_id": job_id,
        }
        for job_id in set(job_ids)
    ]

    with get_db() as db:
        stmt = insert(SentJob).values(values)

        stmt = stmt.on_conflict_do_nothing(
            index_elements=[
                SentJob.user_email,
                SentJob.job_id,
            ]
        )

        db.execute(stmt)
        
def get_unsent_job_ids(
    user_email: str,
    job_ids: list[str],
) -> set[str]:
    user_email = user_email.strip().lower()

    if not job_ids:
        return set()

    with get_db() as db:
        rows = db.execute(
            select(SentJob.job_id).where(
                SentJob.user_email == user_email,
                SentJob.job_id.in_(job_ids),
            )
        ).scalars().all()

        sent_ids = set(rows)

    return set(job_ids) - sent_ids

