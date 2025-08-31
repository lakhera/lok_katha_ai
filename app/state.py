
class AppState:
    story: str = ""
    translation: str = ""
    images_b64: list[str] = []
    backend_story: tuple[str,str] = ("","")
    backend_translate: tuple[str,str] = ("","")
state = AppState()
