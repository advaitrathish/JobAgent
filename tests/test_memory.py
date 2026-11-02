"""Manual memory setup/check. Run explicitly with python."""

from app.memory import agent_memory


if __name__ == "__main__":
    print("Testing JobAgent memory...")
    agent_memory.remember_preference(
        "preferred_locations",
        ["Palakkad", "Thrissur", "Kochi", "Bengaluru", "Mumbai", "Pune",
         "Hyderabad", "Kerala", "Thiruvananthapuram", "Remote India"],
    )
    agent_memory.add_lesson("Always prioritize relevant jobs over application quantity.")
    agent_memory.remember_fact("Python is the user's primary confident programming language.")
    print("\nStored preference:")
    print(agent_memory.get_preference("preferred_locations"))
    print("\nStored lessons:")
    print(agent_memory.get_lessons())
    print("\nStored facts:")
    print(agent_memory.get_facts())
    print("\nMemory test completed!")
