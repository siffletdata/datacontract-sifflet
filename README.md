# datacontract-sifflet

Export an [ODCS](https://opendatacontract.org) data contract to [Sifflet monitors as code](https://docs.siffletdata.com/docs/monitors-as-code).

The command reads a contract from a local path, an `http(s)` URL, or an `s3://` URL, the same way `datacontract-cli` does, and writes one YAML file of monitor documents. It does not call the Sifflet API. Apply the file with the Sifflet CLI.

`datacontract export sifflet` does not load this package. Custom formats are only available through the datacontract Python library, so this package ships its own command.

## Install

```bash
pip install datacontract-sifflet
```

Requires Python 3.10–3.14 and `datacontract-cli` 1.x (`>=1.2,<2`).

## Export

```bash
datacontract-sifflet export orders.odcs.yaml --output monitors/orders.yaml
```

| Option | Meaning |
|---|---|
| `LOCATION` | Local path, `http(s)` URL, or `s3://` URL of the contract. |
| `--output` | File to write. Without it, the monitors are printed to stdout. |
| `--server` | Server in the contract to export. Defaults to the first one. |
| `--schema-name` | One schema name, or `all` (the default). |
| `--debug` | Debug logs, and the full traceback if the export fails. |

Skipped rules are reported as warnings on stderr.

From Python, import the package once so the exporter is registered, then call `export`:

```python
import datacontract_sifflet
from datacontract.data_contract import DataContract

monitors = DataContract(data_contract_file="orders.odcs.yaml", server="production").export("sifflet")
```

## Apply the monitors

`examples/orders.odcs.yaml` is a contract you can export. `examples/workspace.yaml` includes `monitors/*.yaml`. From `examples/`:

```bash
datacontract-sifflet export orders.odcs.yaml --output monitors/orders.yaml
sifflet code workspace apply --file workspace.yaml
```

Replace the workspace `id` with one from `sifflet code workspace init` before applying to a real tenant. Several monitors are written in that one file, separated by `---`, which is the [format the monitor schema documents](https://docs.siffletdata.com/docs/monitor-schema) for more than one monitor per file.

## What is exported

Library rules and SQL rules become monitors. The schema also adds implicit monitors unless you turn them off: schema change, a composite primary key, and, per column, `required`, `unique` or a single-column primary key, the `email` and `uuid` formats, and `pattern`.

Set `sifflet.*` custom properties on the contract, a server, a schema, a property, or a quality rule. The most specific value wins.

| Property | Where it is read | Effect |
|---|---|---|
| `sifflet.enabled` | contract, schema, property, rule | `false` on a rule skips that rule. `false` on a property, schema, or the contract also skips the implicit monitors and quality rules under it, unless a more specific level sets it back to `true`. Defaults to `true`. |
| `sifflet.implicitMonitors` | contract, schema, property | `false` drops the implicit monitors under that level. Defaults to `true`. |
| `sifflet.datasource` | contract or server | Sifflet source name. The server value wins over the contract. |
| `sifflet.datasourceId` | contract or server | Sifflet source id. |
| `sifflet.datasetId` | schema | Sifflet dataset id. The dataset name is the schema `physicalName`, or `name`. |
| `sifflet.friendlyId` | quality rule | Monitor `friendlyId`. Then the rule `id`, then its `name` in snake case. |
| `sifflet.name` | quality rule | Monitor name. |
| `sifflet.severity` | contract, schema, property, rule | `Low`, `Moderate`, `High`, or `Critical`. |
| `sifflet.schedule` | contract, schema, property, rule | Cron expression or a `@daily`-style macro. |
| `sifflet.incidentMessage` | contract, schema, property, rule | Incident message. A rule falls back to its `description`. |
| `sifflet.createOnFailure` | contract, schema, property, rule | Boolean. An explicit `false` is kept. |
| `sifflet.notifications` | contract, schema, property, rule | List of notification objects. |
| `sifflet.tags` | contract, schema, property, rule | List of tag objects. |
| `sifflet.threshold` | quality rule | Threshold object, used as written. |
| `sifflet.parameters` | quality rule | Merged into the monitor parameters. It cannot change `kind`. |

A server only contributes `sifflet.datasource` and `sifflet.datasourceId`. Other `sifflet.*` keys on a server are ignored.

ODCS `severity` is used when `sifflet.severity` is not set on the rule: `info` → `Moderate`, `warning` → `High`, `error` → `Critical`. Anything else becomes `Moderate`, with a warning. The default is `Moderate`.

An ODCS `schedule` is used when `sifflet.schedule` is not set on the rule. A scheduler other than cron drops the schedule and does not fall back to an inherited one.

In a SQL query, `${object}` becomes the fully qualified table name: the server's `project`, or else `catalog`, or else `database`, then its `dataset` or else `schema`, then the table. Each part is quoted for the server's dialect. `${table}` and `${model}` stay the table name.

Library metrics map as follows. A metric with no equivalent at that level is skipped.

| Metric | Level | Monitor |
|---|---|---|
| `rowCount` | table | `Volume` |
| `duplicateValues` | table, with `arguments.properties` | `FieldDuplicates` on the physical names of those properties |
| `duplicateValues` | table, without columns | `RowDuplicates` |
| `nullValues`, `missingValues` | column | `FieldNulls` (`Percentage` when `unit` is `percent`) |
| `invalidValues` with `validValues` | column | `FieldInList` |
| `invalidValues` with `pattern` | column | `FieldFormat` regex |
| `duplicateValues` | column | `FieldDuplicates` on that column |

`missingValues` only monitors NULL. Listed placeholders such as `""` are ignored, with a warning. `arguments.properties` on a column-level `duplicateValues` rule is ignored. On a table-level rule, each name is a schema property: the monitor uses its `physicalName`, or its `name`. Unknown names are ignored, with a warning. If none match, the rule is skipped.

A rule with no operator is skipped, except a SQL rule, which is exported without a threshold so Sifflet's dynamic threshold applies, and the kinds that already alert on any violation (`FieldInList`, `FieldFormat`, `FieldDuplicates`) when the bound is exactly zero or absent.

## Limits

- `type: custom` (including `engine: sifflet`) and `type: text` are not exported.
- A rule `id` or `name` is copied to `friendlyId` without the table name. Sifflet requires a `friendlyId` to be unique on a dataset, so give every rule on the same table its own `id`. The same `id` on two different tables is allowed.
- A computed id includes the threshold, for example `orders_library_row_count_gt_1000`. Changing the threshold changes the id, so Sifflet deletes the monitor and creates a new one, and the run history is lost. Set `sifflet.friendlyId` or `id` when the threshold may change.
- Without `sifflet.datasource`, the source name is the contract's server name, such as `production`. That name usually does not match the source in Sifflet. Set `sifflet.datasource` to the source name shown in Sifflet.
- Nested properties are not exported.
- A SQL rule with no `sifflet.friendlyId`, `id`, or `name` is skipped.

## Development

```bash
uv sync --group dev
uv run pytest
```
