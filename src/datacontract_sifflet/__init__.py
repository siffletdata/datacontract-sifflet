"""Register the Sifflet exporter with datacontract-cli on import."""

from datacontract.export.exporter_factory import exporter_factory

from datacontract_sifflet.exporter import SiffletExporter

__all__ = ["SiffletExporter"]


def _register() -> None:
    """Register ``sifflet``, replacing the exporter bundled in datacontract-cli when present.

    ``ExporterFactory.create`` lets a lazy registration win over ``register_exporter``.
    datacontract-cli still ships its own ``sifflet`` exporter, so that entry has to be
    removed or ``DataContract.export("sifflet")`` would keep using it.
    """
    lazy = getattr(exporter_factory, "dict_lazy_exporter", None)
    if isinstance(lazy, dict):
        for name in [key for key in lazy if str(key) == "sifflet" or getattr(key, "value", None) == "sifflet"]:
            lazy.pop(name, None)
    exporter_factory.register_exporter("sifflet", SiffletExporter)


_register()
