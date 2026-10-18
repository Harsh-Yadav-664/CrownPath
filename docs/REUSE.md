# CrownPath reuse ledger

This file logs every file or data asset lifted from our prior open-source tool swiftPentest
(../swiftpentest-fork, MIT) into CrownPath, for the README disclosure (Rule 11, BUILD_SPEC
§5). Each row: what was copied, from where, to where, and how it was adapted.

| Source (in swiftpentest-fork) | Destination (in crownpath) | What / adaptation | Issue |
|---|---|---|---|
| `config/knowledge/techniques.jsonl` | `data/taxonomy/techniques.jsonl` | vulnerability technique templates → `Technique` nodes | #14 |
| `config/knowledge/chains.jsonl` | `data/taxonomy/chains.jsonl` | chains-with edges → `CHAINS_TO` edges (endpoints are classes + outcome slugs; `xss-reflected` aliased to `xss`) | #14 |
| `config/knowledge/remediation.tsv` | `data/taxonomy/remediation.tsv` | per-class fix text for agent output | #14 |
| `config/classes.jsonl` | `data/taxonomy/classes.jsonl` | canonical class registry (covers classes with no technique template, e.g. csrf) | #14 |
| `lib/finding.py` (`create_finding`) | `docs/findings.schema.json` | finding record shape → ingest contract (schema only, code written fresh) | #5 |
| `lib/sarif.py` | (reference only) | SARIF field names informed the contract; not copied | #5 |
| `bin/demo_target.py` | `data/demo_target.py` (pending) | stdlib-only intentionally-weak localhost target → reused for the optional live capture (E2) | #24 |

swiftPentest's agent swarm, hooks, DAG engine, and in-memory chain walker (`lib/kb.py`) are
deliberately NOT reused (§5).
