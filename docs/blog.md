One IDOR, Four Attack Paths Gone: Building CrownPath on FalkorDB
================================================================

A security scanner can tell you that you have 200 vulnerabilities. It cannot necessarily tell you which one to fix first to stop an attacker from reaching your most valuable data.

That is the problem we wanted to solve with **CrownPath**, our attack-path triage agent built on FalkorDB for Graph Hacks by WeMakeDevs.

Our demo produced a concrete answer: **fix the IDOR on /api/orders, and four of the six modeled attack paths to the customer database disappear—including the highest-scoring path.**

That number isn't an LLM's opinion. It's the result of traversing a graph, counting paths, and checking what changes when the finding is removed.

Here's how we built it, why the graph matters, and what we learned about making security recommendations explainable.

The problem with ranking vulnerabilities in isolation
-----------------------------------------------------

Imagine a storefront with an orders API, an admin console, and a customer database. A scanner finds an XSS vulnerability, an IDOR, and several other weaknesses.

A conventional report gives you individual findings, severity scores, and perhaps remediation advice. But attackers don't necessarily exploit vulnerabilities one at a time. They chain opportunities together.

An exposed entry point might lead to session theft. A compromised identity might reach an API. That API might expose a route to sensitive customer data.

The risk isn't just in the individual findings. It's in the connections between them.

We wanted CrownPath to answer a more useful question:

**Which remediation removes the greatest number of routes to the assets we care about most?**

That requires reasoning about reachability, not merely sorting a list.

Why FalkorDB is the foundation, not a feature
---------------------------------------------

CrownPath models the environment as a property graph with five node types:

*   **Asset:** Applications, services, hosts, and databases.
    
*   **Endpoint:** Routes exposed by those assets.
    
*   **Finding:** Discovered vulnerabilities, with confidence and verification status.
    
*   **Technique:** The attack capability associated with a finding.
    
*   **Identity:** An anonymous, user, or privileged identity.
    

Eight relationship types connect these nodes, representing exposure, findings, privilege grants, access, network connectivity, and technique chaining.

The important design decision is that these relationships have meaning. They aren't decorative links between objects.

FalkorDB stores the estate, and Cypher traversals discover the attack paths. The same graph supports path scoring, remediation analysis, and scan-to-scan comparisons.

Remove the graph, and CrownPath loses the computations that make its recommendations possible.

<img width="930" height="678" alt="image" src="https://github.com/user-attachments/assets/7a5eec3f-1f73-423b-8713-86d975d666bf" />


The rule that keeps the graph honest
------------------------------------

Not every scanner result should become an assumed attack capability.

CrownPath distinguishes three finding states: confirmed, inconclusive, and refuted.

Only confirmed findings receive the attack-enabling relationships used by the path analysis. Inconclusive and refuted findings remain available for audit, but cannot silently become links in an attack chain.

This matters because a graph can make incorrect assumptions look convincing. A beautifully rendered path is still misleading if one of its edges represents an unverified vulnerability.

We carried forward the findings schema and vulnerability taxonomy from our earlier open-source tool, swiftPentest, and disclosed that reuse in the repository. The FalkorDB graph layer, path queries, agent, and explainability output were built for this hackathon.

Finding the paths to the crown jewel
------------------------------------

Our demonstration uses a synthetic estate containing four assets, six endpoints, three identities, and eight findings. One finding is deliberately inconclusive.

The target is the customer database, designated as a crown jewel. CrownPath starts at unauthenticated endpoints and traverses the permitted relationships to discover routes to that target.

The core query uses a variable-length Cypher match:

Plain textANTLR4BashCC#CSSCoffeeScriptCMakeDartDjangoDockerEJSErlangGitGoGraphQLGroovyHTMLJavaJavaScriptJSONJSXKotlinLaTeXLessLuaMakefileMarkdownMATLABMarkupObjective-CPerlPHPPowerShell.propertiesProtocol BuffersPythonRRubySass (Sass)Sass (Scss)SchemeSQLShellSwiftSVGTSXTypeScriptWebAssemblyYAMLXML`   MATCH path = (e:Endpoint {auth_required:false})        -[:EXPOSES|HAS_FINDING|LEADS_TO|GRANTS|CAN_ACCESS|CONNECTS_TO*1..8]->        (j:Asset {is_crown_jewel:true})  RETURN path  ORDER BY length(path)   `

The query returns six paths in our demo graph.

The significance isn't the number six. It's that each result is an explicit route through connected security data. CrownPath can inspect those routes, score them, and show the evidence behind a recommendation.

The interesting part: finding the choke point
---------------------------------------------

Finding attack paths is useful. Identifying the finding whose remediation breaks the most of them is the more interesting problem.

CrownPath enumerates the paths, extracts the Finding nodes on each one, and counts how many paths contain each finding.

Conceptually, the analysis asks:

1.  How many attack paths reach the crown jewel?
    
2.  Which findings occur on those paths?
    
3.  How many paths would each finding's removal eliminate?
    
4.  Which candidate also appears on the highest-scoring path?
    

The result:

**f:idor — four of six paths severed.**

The IDOR appears on four of the six paths, including the highest-scoring one. We then tested the claim directly: remove that finding from the demo graph and run the traversal again. Two paths remain.

That gives us a verifiable before-and-after result, rather than a recommendation that depends on trusting an agent's explanation.

<img width="935" height="698" alt="image" src="https://github.com/user-attachments/assets/829debf2-2a42-4ef1-a9d3-300cd340c49e" />


### Why not just use betweenness centrality?

We also cross-checked the result using FalkorDB's betweenness algorithm. It did not rank the IDOR first.

That was instructive, not a failure.

Betweenness centrality measures how frequently a node bridges pairs of nodes across the graph. Our question is narrower: how many paths from an anonymous entry point to a particular crown jewel contain a finding?

Those are different metrics, and they can produce different rankings.

For our remediation question, counting the relevant paths directly is the authoritative method. Centrality is a useful sanity check, but it isn't a substitute for the metric we're actually trying to optimize.

Scoring paths without pretending to predict the future
------------------------------------------------------

CrownPath scores each path using the product of the confidence values of its findings, multiplied by the crown jewel's business value, and divided by the path length:

\[\\text{Score}(p)=\\frac{V\_{\\text{jewel}}\\prod\_{f\\in p}C\_f}{L(p)}\]

Here, (C\_f) is a finding's confidence, (V\_{\\text{jewel}}) is the target asset's assigned value, and (L(p)) is the path length.

The intent is to combine evidence confidence, potential impact, and path length into a prioritization heuristic.

This is not a calibrated probability of exploitation. It is a transparent scoring rule for comparing modeled paths. That distinction matters when the output informs security decisions.

Where the agent fits
--------------------

The LLM is not responsible for inventing attack paths or deciding the underlying path counts.

CrownPath exposes six graph tools through an MCP server. The agent can call those tools to discover paths, rank remediation options, inspect choke points, and retrieve relevant evidence. Its response cites the paths that support its recommendation.

A FastAPI backend and Cytoscape-based interface make those paths visible. Instead of reading a paragraph and taking it on faith, a reviewer can inspect the connected nodes and see why a particular finding matters.

There is also a deterministic mode that runs without an LLM API key. That gives us a reproducible baseline and lets the core graph reasoning work without depending on model availability.

We wanted the model to help interpret and communicate the evidence—not replace the computation that establishes it.

The graph remembers what changed
--------------------------------

We also implemented scan-to-scan memory.

Findings carry first\_seen, last\_seen, and scan identifiers. CrownPath compares two scans using Cypher and reports findings that appeared or disappeared, along with changes in reachability.

In our demonstration, the earlier scan has two paths to the customer database. A later scan introduces a confirmed IDOR, and the count rises to six. CrownPath flags the Orders API as regressed.

We considered Graphiti, but our findings already have structured identities, timestamps, and verification states. For this use case, native graph queries keep the comparison deterministic without requiring an LLM to extract entities from unstructured history.

That makes the memory useful for a practical security question: not just _what is vulnerable now?_, but _what changed, and did that change create new ways to reach sensitive data?_

What we verified—and what we haven't claimed
--------------------------------------------

We tested the graph queries against FalkorDB, including the choke-point result and the post-removal path count. The repository also includes tests, local Docker setup instructions, and a larger synthetic estate.

One implementation detail caught us off guard: LIMIT did not reliably bound variable-length path enumeration in our FalkorDB testing. A limit at or below the true result count returned too few rows. We therefore enumerate the relevant paths and slice the list used for display afterward.

Our default scenario is synthetic, making the expected results reproducible. We also provide an optional capture workflow against an intentionally vulnerable application bound to loopback; it refuses other hosts. We do not present this demonstration as a production security assessment.

AI coding assistance, including Claude Code, was used and is disclosed in the repository. We verified the implementation and documented the reused material rather than presenting prior work as new.

The takeaway
------------

CrownPath began with a simple frustration: a list of vulnerabilities doesn't necessarily tell a security team what to fix first.

A graph gives us another way to ask the question. It connects findings to identities, assets, and reachable targets, making it possible to evaluate remediation by the attack paths it removes.

In our demo, the answer was not the finding with the most impressive severity label. It was the IDOR that sat on four of six paths to the customer database.

That's the idea behind CrownPath: **prioritize the fix that removes the most dangerous routes, and show the evidence for why it matters.**

### Explore CrownPath

*   **Source code:** [https://github.com/Harsh-Yadav-664/CrownPath](https://github.com/Harsh-Yadav-664/CrownPath)
    
*   **Live demo:** [https://crownpath-v9kt.onrender.com/](https://crownpath-v9kt.onrender.com/)
    
*   **Hackathon:** [https://www.wemakedevs.org/hackathons/falkordb](https://www.wemakedevs.org/hackathons/falkordb)
    

The repository includes the graph model, Cypher queries, MCP server, setup instructions, and test suite. The live demo may take around a minute to wake on Render's free tier.
