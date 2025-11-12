from typing import Protocol, Optional

class SearchError(Exception):
    pass

class Adapter(Protocol):
    def search(self, *, query: str, timeout: float, browser: bool, lang: Optional[str], limit: int) -> list[dict]:
        ...

def get_adapter(country: str):
    c = country.lower()
    if c == "fr":
        from . import fr as module
        return module
    if c == "de":
        from . import de as module
        return module
    if c == "pl":
        from . import pl as module
        return module
    raise SearchError(f"Unsupported country '{country}'. Supported: fr, de, pl")