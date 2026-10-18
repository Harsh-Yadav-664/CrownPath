# Acme Shop

Acme Shop is a synthetic e-commerce app we modelled ourselves for this demo: no real company, no real deployment, and no third-party data.

## What it is

An online shop split across four assets. The internet-facing **Storefront** web app serves search, a redirect helper and the login page. Behind it sit an internal **Orders API**, an **Admin console**, and the **Customer database**, which is the crown jewel (business value 100 on a 0-100 scale). Four endpoints answer anonymous visitors: `/search`, `/go` and `/login` on the Storefront, plus a `/metrics` page left open on the Orders API host. `/api/orders` and `/admin` need a login. People reach the estate as one of three identities: an anonymous visitor, a logged-in customer (user), or an admin.

## Why these findings

The eight findings are the kind a routine web-app scan of a shop like this turns up, and together they show why severity alone picks the wrong fix:

- Three medium bugs any anonymous visitor can reach (a reflected XSS on `/search`, an open redirect on `/go`, an authentication bypass on `/login`) each give an attacker a logged-in customer session.
- A customer session can call the Orders API, where an IDOR on `/api/orders` returns other customers' records straight from the Customer database.
- An unauthenticated SSRF on `/metrics` pivots into the Admin console, which reaches the database through SQL injection or through a mass-assignment flaw that makes the attacker an admin.
- A CSRF on `/search` is only inconclusive. It stays in the graph for audit but is never part of an attack path, because only confirmed findings can be.

The highest-severity finding (the SQL injection, CVSS 9.0) sits on one of the six attack paths to the Customer database. The IDOR (CVSS 8.1) sits on four of them. That gap is the point of the demo.

## Why synthetic (Rule 6)

Hackathon Rule 6 allows only data we own or generate. The estate is generated deterministically by `data/gen_findings.py` from `docs/demo-scenario.md`, so every run builds the same graph and gives the same "4 of 6" answer. The synthetic findings carry no captured evidence; their numbers (CVSS, confidence) are set by hand to be realistic.

To show the same pipeline works on real scanner output, `data/capture_findings.py` probes our own deliberately weak app (`data/demo_target.py`, bound to 127.0.0.1 only) and writes `data/findings.captured.json`, with the evidence it observed. That file loads through the same ingest path into its own graph. Nothing is ever pointed at a third-party host.

## A bigger estate

The demo keeps Acme Shop small so the answer fits on one screen. `python data/gen_findings.py --scenario large` writes `data/findings.large.json`, the whole shop at a more realistic size: 20 assets in three tiers (internet-facing apps, internal services, data stores), 6 identities, 25 endpoints and 22 findings, with three crown jewels: the Customer database, the Payment card vault and the Cloud secrets manager. It is also synthetic and deterministic, and it loads into its own graph (`make seed-large`, graph `crownpath_large`), so the default demo and its "4 of 6" never change.

The same graph queries give a different answer for each crown jewel. All 5 routes to the card vault pass through one insecure-deserialization bug on the Payments service. The customer database has 7 routes split between an IDOR and an SSO mass-assignment flaw (3 each). The two most severe findings (a 9.8 RCE on staging and an 8.8 file upload on the CMS) lie on no route to any crown jewel.
