
from app.ai_client import ai_client
from app.memory import agent_memory
from app.knowledge_base import knowledge_base


class JobAgent:
    """Central AI agent for JobAgent."""

    def __init__(self):
        self.ai = ai_client
        self.memory = agent_memory
        self.knowledge = knowledge_base

    def get_context(self):
        """Collect relevant career knowledge and memory."""

        profile = self.knowledge.get_all_information()
        preferences = self.memory.get_preference(
            "preferred_locations",
            [],
        )
        lessons = self.memory.get_lessons()

        return {
            "career_profile": profile,
            "preferred_locations": preferences,
            "lessons": lessons,
        }

    def respond(self, instruction):
        """Generate an AI response using the available context."""

        if not instruction or not instruction.strip():
            raise ValueError("Instruction cannot be empty.")

        context = self.get_context()

        system_prompt = f"""
You are JobAgent, an intelligent personal job-search assistant.

Use the user's actual career information and preferences.
Never invent qualifications, experience, certifications, or skills.
Be accurate, professional, and helpful.

User context:
{context}
"""

        response = self.ai.generate(
            prompt=instruction,
            system_prompt=system_prompt,
        )

        return response

    def remember_feedback(self, feedback):
        """Store feedback for future improvement."""

        self.memory.add_lesson(feedback)


# Shared JobAgent instance
job_agent = JobAgent()
