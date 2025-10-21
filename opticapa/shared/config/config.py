import json
import logging

from dotenv import find_dotenv, load_dotenv
from pydantic_settings import BaseSettings
from pytz import timezone, tzfile


class Settings(BaseSettings):
    loglevel: int = logging.DEBUG
    server_port: int = 8000
    environment: str = "develop"
    kube_namespace: str = "local"
    coac_pe_incomp: bool = True

    # Excel settings
    show_logs_excel: bool = False
    excel_chunk_size: int = 10

    # Publication settings
    # The following id is used to represent the working version of publications.
    # Partitioned tables are created from this version which is the default version.
    working_version_id: int = 0

    db_url: str
    show_logs_db_stmt: bool = False
    db_superuser_username: str
    db_superuser_password: str
    db_statement_timeout: int = 180000  # In ms, default value is align to pods timeout

    fid_client_id: str
    fid_client_secret: str
    fid_issuer: str
    fid_discovery_url: str
    fid_redirect_url: str

    jwt_secret_key: str
    jwt_refresh_secret_key: str

    algorithm: str
    access_token_expire_minutes: int
    refresh_token_expire_minutes: int
    api_to_api_token_expire_minutes: int
    bucket_name: str = ""

    fid: str
    fid_certificate: str

    frontend_url: str
    timezone_name: str = "Europe/Paris"

    # Datadog settings
    activate_dd_monitoring: bool = False
    datadog_service_name: str = ""
    datadog_port: int = 8125
    raw_datadog_routes_monitor: str = (
        '{"routes": [["lignes_voies", "GET"]]}'  # json format
    )

    @property
    def timezone(self) -> tzfile:
        return timezone(self.timezone_name)

    def db_params(self) -> dict:
        conn_string = self.db_url.split("//")[-1].split("@")
        user, pwd = conn_string[0].split(":")[0], conn_string[0].split(":")[1]
        db_name = conn_string[1].split("/")[1]
        server_url, server_port = (
            conn_string[1].split("/")[0].split(":")[0],
            conn_string[1].split("/")[0].split(":")[1],
        )
        return dict(
            user=user, pwd=pwd, db_name=db_name, url=server_url, port=server_port
        )

    def datadog_routes_monitor(self) -> list[tuple[str, str]]:
        routes = json.loads(settings.raw_datadog_routes_monitor)["routes"]
        datadog_routes_monitor: list[tuple[str, str]] = []
        for route_path, method in routes:
            datadog_routes_monitor.append((route_path.lower(), method.upper()))
        return datadog_routes_monitor


load_dotenv(
    dotenv_path=find_dotenv(raise_error_if_not_found=False),
    verbose=False,
    override=False,
)
settings = Settings()
