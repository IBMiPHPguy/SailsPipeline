DEFAULT_PAGE_SIZE = 10
PAGE_SIZE_OPTIONS = (10, 15, 25, 50, 100)
PAGE_SIZE_MAX = 100


def normalize_page_size(page_size: int, *, default: int = DEFAULT_PAGE_SIZE, maximum: int = PAGE_SIZE_MAX) -> int:
    try:
        size = int(page_size)
    except (TypeError, ValueError):
        return default
    return max(1, min(size, maximum))
