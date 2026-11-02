
import json

from app import config


class KnowledgeBase:
    """Manage JobAgent's career and job-search knowledge."""

    def __init__(self):
        self.file_path = config.DATA_DIR / "knowledge.json"
        config.DATA_DIR.mkdir(parents=True, exist_ok=True)

        if not self.file_path.exists():
            self._save({})

    def _load(self):
        try:
            with self.file_path.open("r", encoding="utf-8") as file:
                return json.load(file)

        except (json.JSONDecodeError, OSError):
            return {}

    def _save(self, data):
        with self.file_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=4, ensure_ascii=False)

    def set_information(self, category, information):
        """Save information under a category."""

        data = self._load()
        data[category] = information
        self._save(data)

    def get_information(self, category, default=None):
        """Retrieve information from a category."""

        data = self._load()
        return data.get(category, default)

    def get_all_information(self):
        """Return the complete knowledge base."""

        return self._load()

    def delete_information(self, category):
        """Delete a category."""

        data = self._load()

        if category in data:
            del data[category]
            self._save(data)


# Shared knowledge base instance
knowledge_base = KnowledgeBase()
