"""Manual KnowledgeBase setup/check. Run explicitly with python."""

from app.knowledge_base import knowledge_base


if __name__ == "__main__":
    print("Testing JobAgent knowledge base...")
    knowledge_base.set_information(
        "programming_languages",
        {"Python": "Primary and confident programming language"},
    )
    knowledge_base.set_information(
        "career_preferences",
        {
            "locations": ["Palakkad", "Thrissur", "Kochi", "Bengaluru", "Remote India"],
            "career_goal": "Build a long-term career in AI and IT",
        },
    )
    print("\nProgramming languages:")
    print(knowledge_base.get_information("programming_languages"))
    print("\nCareer preferences:")
    print(knowledge_base.get_information("career_preferences"))
    print("\nKnowledge base test completed!")
