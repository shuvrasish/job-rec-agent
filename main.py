import os
from pathlib import Path
from agent.agent import run_agent


def main():
    resume_path = Path(
        os.getenv("RESUME_PATH", "resumes/resume.pdf")
    ).resolve()

    if not resume_path.exists():
        raise FileNotFoundError(
            f"Resume not found: {resume_path}"
        )

    to_email = os.getenv("EMAIL_TO")
    if not to_email:
        raise RuntimeError(
            "EMAIL_TO is not set."
        )
    
    instructions = f"""
        Find software engineering jobs matching this resume.
        Find jobs in Hyderabad and Bengaluru, India (Preferably Hyderabad or Remote).

        Current Salary: 41 LPA (33 Base + 8 Bonus)

        Requirements:
        - Posted within the last 7 days
        - Software Engineer / SDE / Backend / Full-Stack
        - Strong match with my resume
        - Prefer direct company postings
        - Product Based companies are preferred
        - Offering a salary of 42 LPA or more (Base + Bonus)
    """

    result = run_agent(
        resume_path=str(resume_path),
        to_email=os.getenv("EMAIL_TO", ""),
        additional_instructions=instructions,
    )

    final_message = result["messages"][-1]

    print(final_message.content)


if __name__ == "__main__":
    main()