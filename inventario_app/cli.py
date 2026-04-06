import click
from flask import current_app

from .services.sqlite_import_service import import_from_sqlite


def register_cli_commands(app) -> None:
    @app.cli.command("show-db-url")
    def show_db_url() -> None:
        click.echo(current_app.config["SQLALCHEMY_DATABASE_URI"])

    @app.cli.command("import-sqlite")
    @click.option(
        "--source", "source_path", required=True, help="Ruta del archivo SQLite origen."
    )
    @click.option(
        "--reset-target",
        is_flag=True,
        help="Limpia la base destino antes de importar.",
    )
    def import_sqlite_command(source_path: str, reset_target: bool) -> None:
        imported_counts = import_from_sqlite(source_path, reset_target=reset_target)
        for table_name, count in imported_counts.items():
            click.echo(f"{table_name}: {count}")
