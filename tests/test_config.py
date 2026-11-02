"""Manual configuration check. Run explicitly with python."""

from app import config


if __name__ == "__main__":
    print("JobAgent configuration loaded!")
    print("Application:", config.APP_NAME)
    print("API address:", config.LLM_BASE_URL)
    print("Model:", config.LLM_MODEL)
    print("Timezone:", config.TIMEZONE)
    print("API key loaded:", bool(config.LLM_API_KEY))
