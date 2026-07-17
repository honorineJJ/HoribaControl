from __future__ import annotations

from .factory import create_controller
from .gui import MicroHRApp


def main() -> None:
    controller, config = create_controller("config.yaml")
    app = MicroHRApp(controller, config)
    app.mainloop()


if __name__ == "__main__":
    main()
