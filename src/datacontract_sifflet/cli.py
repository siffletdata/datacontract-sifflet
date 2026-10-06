"""Command line for exporting an ODCS data contract to Sifflet monitors as code.

``datacontract export sifflet`` cannot load this exporter: datacontract-cli only
exposes custom formats through the Python library. This command is the supported
way to run the export.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

import typer
from datacontract.data_contract import DataContract
from datacontract.model.exceptions import DataContractException
from typing_extensions import Annotated

import datacontract_sifflet  # noqa: F401  # registers the exporter

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
)


@app.callback()
def callback() -> None:
    """Export an ODCS data contract to Sifflet monitors as code."""


def _configure_logging(debug: bool) -> None:
    """Show skipped-rule warnings. ``--debug`` also prints debug logs and tracebacks."""
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.WARNING,
        format="%(levelname)s %(message)s",
        stream=sys.stderr,
        force=True,
    )


def _export(location: str, server: Optional[str], schema_name: str) -> str:
    result = DataContract(data_contract_file=location, server=server).export("sifflet", schema_name=schema_name)
    if not isinstance(result, str):
        raise RuntimeError("Sifflet export did not return text.")
    return result


@app.command(
    epilog="Example: datacontract-sifflet export orders.odcs.yaml --output monitors.yaml",
)
def export(
    location: Annotated[
        str,
        typer.Argument(help="Location of the data contract YAML: a local path, an http(s) URL, or an s3 URL."),
    ],
    output: Annotated[
        Optional[Path],
        typer.Option(help="File where the monitors are written. Printed to stdout when omitted."),
    ] = None,
    server: Annotated[
        Optional[str],
        typer.Option(help="Server to export. The first server in the contract is used when omitted."),
    ] = None,
    schema_name: Annotated[
        str,
        typer.Option("--schema-name", help="Schema to export, for example `orders`, or `all` for every schema."),
    ] = "all",
    debug: Annotated[bool, typer.Option("--debug", help="Print debug logs and the full traceback on failure.")] = False,
):
    """Export quality rules to Sifflet monitors as code.

    Datasource, severity, and schedule are read from ``sifflet.*`` custom properties
    on the contract. Nothing is sent to the Sifflet API.
    """
    _configure_logging(debug)
    try:
        result = _export(location, server, schema_name)
    except Exception as error:
        if debug:
            raise
        message = error.reason if isinstance(error, DataContractException) else str(error)
        print(f"Error: {message}", file=sys.stderr)
        print("Pass --debug for the full traceback.", file=sys.stderr)
        raise typer.Exit(code=1) from None

    if output is None:
        sys.stdout.write(result)
        if not result.endswith("\n"):
            sys.stdout.write("\n")
        return

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(result, encoding="utf-8")
    print(f"Written result to {output}", file=sys.stderr)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
