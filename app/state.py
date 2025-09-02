
# AppState
# Description: Holds the application state for the story, translation, images, and backend information.
# Requires: Pydantic

class AppState:
    story: str = ""
    translation: str = ""
    images_b64: list[str] = []
    backend_story: tuple[str,str] = ("","")
    backend_translate: tuple[str,str] = ("","")
state = AppState()
