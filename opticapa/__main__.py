import argparse

import uvicorn
from opticapa_models.scripts.init_db import DatabaseService

from opticapa.shared.config.config import settings


def run_local(port=settings.server_port):
    uvicorn.run(
        "opticapa.main:app", port=port, reload=True, log_level=settings.loglevel
    )


def main():

    parser = argparse.ArgumentParser(description="Process Backend")
    parser.add_argument(
        "action",
        choices=["serve", "init_db"],
        default="serve",
        help="Choose the action : serve backend or run init db",
    )

    args = parser.parse_args()

    dic = {
        "serve": (run_local, {"port": settings.server_port}),
        "init_db": (DatabaseService(url=f"postgresql://{settings.db_url}"), {}),
    }
    action, action_args = dic[args.action]
    action(**action_args)


if __name__ == "__main__":
    main()
