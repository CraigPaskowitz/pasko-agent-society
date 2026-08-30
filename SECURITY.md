# Security and Safety Reports

Pasko Agent Society Gate 1 is deliberately synthetic and has no agent-facing external I/O. Please report any issue that could violate `SAFETY.md` through a private GitHub Security Advisory for this repository.

High-priority reports include any route from an agent-controlled value to a host path, URL, command, dynamic execution, process, network client, browser, credential, connector, or external message; any way for `READ_SEALED_CACHE` to execute; any state mutation without ledger provenance; or any communication target outside declared simulator IDs.

Do not probe real systems while investigating a report. A minimal synthetic test case is sufficient.
