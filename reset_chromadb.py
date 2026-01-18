import os
import shutil

_BASE_DIR = os.path.dirname(__file__)
_CHROMA_DIR = os.path.join(_BASE_DIR, "chroma_db")


def main() -> None:
    if not os.path.exists(_CHROMA_DIR):
        print(f"[reset] nothing to do: {_CHROMA_DIR} does not exist")
        return

    shutil.rmtree(_CHROMA_DIR)
    print(f"[reset] removed: {_CHROMA_DIR}")


if __name__ == "__main__":
    main()
