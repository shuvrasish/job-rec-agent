import sys

from agent.agent import agent


def main():
    content = f"""
        Find software engineering jobs matching this resume.

        The resume is located at: resumes/resume.pdf

        Find jobs in Hyderabad and Bengaluru, India (Preferably Hyderabad or Remote).

        Requirements:
        - 3 – 6 years of experience
        - Posted within the last 7 days
        - Software Engineer / SDE / Backend / Full-Stack
        - Strong match with my resume
        - Prefer direct company postings
    """

    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": content
                }
            ]
        }
    )

    final_message = result["messages"][-1]

    print(final_message.content)


if __name__ == "__main__":
    main()