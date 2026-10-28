# NextGen Guardians — a guardrail proxy for every AI call

**Team:** NextGen Guardians
**Track:** Developer
**Use case:** Cybersecurity (SOC-style triage of AI traffic) — with an external-business data-leak extension
**Source (open):** https://github.com/TowardInfinity/aegis-proxy

The full product is exported under [`aegis-proxy/`](./aegis-proxy/) in this folder; it is a
single Go binary plus a React SecOps console. Nothing secret is included — real keys live in
an untracked `config.yaml` / `.env`; only `.env.example` and `config.example.yaml` ship.

## What it is
Every AI request (Claude Code, pi, an internal "AIPro" app) is pointed at this proxy instead of
straight at the provider. The employee never holds a provider key. Each request runs a pipeline:

> validate → redact (PII/secrets → `⟦PII⟧` tokens) → **judge** → cache → budget → route →
> response-scan → ledger

## Why this is the cybersecurity use case
The brief asks for a SOC alert-triage agent: *assign severity with a stated reason, group related
items, hand anything above a threshold to a human, and treat the content as untrusted data — never
as instructions.* That is exactly what the proxy does, with each AI request as the "alert":

| Brief requirement | How NextGen Guardians does it |
|---|---|
| Assign severity **with a stated reason** | An LLM judge scores each request; risk = strongest signal ×100, banded MEDIUM 30+/HIGH 60+/CRITICAL 80+, with the triggering reason recorded. |
| Hand anything above a threshold to a **human** | Confidential-data or "malicious cyber" requests → `403/400` on the wire + a `SEC-…` ticket → **held queue** → SecOps approves/rejects in the console. Approved text passes on resend. |
| Treat content as **untrusted, never instructions** | The judge classifies intent; redaction strips secrets *before* anything leaves; the response is scanned on the way back. Prompt text is never obeyed as policy. |
| Group / log everything | Every call is written to an append-only ledger (requests, blocks, spend, cache savings) surfaced in the dashboard. |

Two things it catches: **confidential data leaving** (the external-business angle — a `.env`,
customer list or board pack carried upstream by a "fix the build" request) and **requests for
offensive hacking** (category *malicious cyber*). Defensive work — fixing your own vulnerability,
explaining an attack in general, writing tests or security tooling — is allowed, not blind.

## Run it
See [`aegis-proxy/README.md`](./aegis-proxy/README.md). In short: copy `config.example.yaml` →
`config.yaml` and fill in a provider key, `go build -o guardrail ./cmd/guardrail`, then
`guardrail serve -config config.yaml`. Point `ANTHROPIC_BASE_URL` at the proxy. The SecOps console
is in `web/portal` (`pnpm dev`).
