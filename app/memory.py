
import json
from pathlib import Path
from threading import RLock

from app import config


class AgentMemory:
    """Persistent memory for JobAgent."""

    def __init__(self):
        self.memory_file = config.DATA_DIR / "agent_memory.json"
        self.lock = RLock()

        config.DATA_DIR.mkdir(parents=True, exist_ok=True)

        if not self.memory_file.exists():
            self._save({"preferences": {}, "lessons": [], "facts": []})

    def _load(self):
        """Load memory from disk."""

        try:
            with self.memory_file.open("r", encoding="utf-8") as file:
                return json.load(file)

        except (json.JSONDecodeError, OSError):
            return {"preferences": {}, "lessons": [], "facts": []}

    def _save(self, memory):
        """Save memory to disk."""

        with self.memory_file.open("w", encoding="utf-8") as file:
            json.dump(memory, file, indent=4, ensure_ascii=False)

    def remember_preference(self, key, value):
        """Remember a user preference."""

        with self.lock:
            memory = self._load()
            memory.setdefault("preferences", {})[key] = value
            self._save(memory)

    def get_preference(self, key, default=None):
        """Retrieve a stored preference."""

        with self.lock:
            memory = self._load()
            return memory.get("preferences", {}).get(key, default)

    def add_lesson(self, lesson):
        """Store a lesson learned from feedback."""

        if not lesson or not lesson.strip():
            return

        with self.lock:
            memory = self._load()
            lessons = memory.setdefault("lessons", [])

            if lesson not in lessons:
                lessons.append(lesson)

            self._save(memory)

    def get_lessons(self):
        """Retrieve stored lessons."""

        with self.lock:
            memory = self._load()
            return memory.get("lessons", [])

    def remember_fact(self, fact):
        """Store useful verified information."""

        if not fact or not fact.strip():
            return

        with self.lock:
            memory = self._load()
            facts = memory.setdefault("facts", [])

            if fact not in facts:
                facts.append(fact)

            self._save(memory)

    def get_facts(self):
        """Retrieve stored facts."""

        with self.lock:
            memory = self._load()
            return memory.get("facts", [])


# Shared memory instance
agent_memory = AgentMemory()
