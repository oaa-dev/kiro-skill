---
name: ask
description: Answer questions about the project's structure, flow, architecture, layers, modules, and past issues -- knowledge base first, code second. Also answers general questions directly. Use when the user asks how, where, or why something works in the system.
argument-hint: "[your question]"
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - WebSearch
  - WebFetch
---

# Ask

**Purpose:** Answer any question with the fewest tokens possible. Project questions are answered from the knowledge base first and the code second, with sources. General questions are answered directly. Answers that required real code digging can be saved back to the knowledge base so the next lookup is a single read.

**Read-only on project code.** The only file this skill may write is a saved answer (Step 5).

---

## Process

<step number="1" required="true">
### Step 1: Classify the Question

Read `$ARGUMENTS` as the question. If it's empty, ask the user what they want to know.

Classify it in-context (no tool calls):

| Type | Examples | Next |
|------|----------|------|
| **General** | "Difference between Laravel jobs and events?", "What is ISR in Next.js?" | Answer directly from your own knowledge. Use WebSearch only for version-specific or recent facts. **Skip all other steps.** |
| **System** | "How does checkout work?", "Which layer handles validation?", "Where is the order total calculated?" | Step 2 |
| **History** | "Did we hit N+1 on orders before?", "Any gotchas with the payment module?" | Step 2 -- focus on Critical Patterns, Solutions, and Answers |
| **Mixed** | "Are we using Laravel policies the right way?" | Step 2 for the project part, then add general context |

**Do NOT ask clarifying questions unless the question is truly ambiguous.** Make a reasonable interpretation and state it in one line.
</step>

<step number="2" required="true" depends_on="1">
### Step 2: Knowledge Base Lookup (cheapest first)

Stop as soon as you have enough to answer.

**2a. Read the index.**

```
Read: docs/knowledge/index.md
```

Scan it in-context for matching Critical Patterns, Modules, Solutions, and Answers.

- **Saved answer matches:** read `docs/knowledge/answers/{file}` and check its `sources` files still exist (one Glob). If they exist, answer from it and skip to Step 4. If some are gone, treat the saved answer as a lead, not a fact, and continue.
- **No index and no `docs/knowledge/` directory:** say "No knowledge base found -- run /kg:setup to create one." in one line, then go to Step 3.

**2b. Read the architecture doc (if present).**

```
Read: docs/knowledge/architecture.md
```

Skip silently if it doesn't exist.

**2c. Read matched module docs.**

```
Read: docs/knowledge/modules/{module-name}.md limit:60
```

Use the file map (connected files, components, relationships) to know exactly where to look in code.

**2d. Deep-read strong solution matches** (typically 0-3 files) for History questions or when a solution directly concerns the asked area.
</step>

<step number="3" required="false" depends_on="2">
### Step 3: Targeted Code Search (only if the KB isn't enough)

- Start from the module doc file map. If there is none, use targeted Grep/Glob on names from the question -- never crawl the tree.
- Read only the relevant line ranges, not whole files.
- **Budget: ~8 file reads.** If that's not enough, answer with what you found and list what's still unclear.

Track every file you used -- they become the answer's sources.
</step>

<step number="4" required="true">
### Step 4: Answer

```markdown
[Direct answer in 1-3 sentences]

**How it works**
[Flow or layers, step by step -- or a short ASCII flow when it helps:
route -> middleware -> controller -> service -> model]

**Sources**
- path/to/file.php:42 -- [what it shows]
- KB: modules/order.md, solutions/performance-issues/x.md

**Gaps**
[What the KB didn't cover, e.g. "Payment module has no doc -- run /kg:generate-module-docs Payment". Omit if none.]
```

For General questions, just answer -- no Sources/Gaps sections unless you used the web.
</step>

<step number="5" required="false" depends_on="4">
### Step 5: Offer to Save

**Only** if Step 3 ran (you had to dig into code) **and** the question was System or History, ask in one line:

```
Save this answer to the knowledge base? (y/n)
```

On yes:

1. Write `docs/knowledge/answers/{slug}.md` (slug = short kebab-case of the question, create the directory if missing):

```markdown
---
question: "How does the order checkout flow work?"
modules: [Order, Payment]
tags: [checkout, flow, service-layer]
date: YYYY-MM-DD
sources:
  - app/Http/Controllers/CheckoutController.php
  - app/Services/CheckoutService.php
---

# How does the order checkout flow work?

[The answer from Step 4, without the Gaps section]
```

2. If `docs/knowledge/index.md` exists, add one row to its `## Answers` table (create the section after `## Solutions` if missing) and increment `<!-- Answers: N -->`:

```
| {slug}.md | {question} | {modules} | {tags} | YYYY-MM-DD |
```

Do not run a full reindex.

3. Confirm: "Saved to docs/knowledge/answers/{slug}.md."
</step>

---

## Guidelines

- Never edit project code. Never spawn agents.
- Read the index first -- one Read replaces many Grep calls.
- Distill, don't dump file contents.
- Cite `path:line` for every claim about the code.
- If you can't find it, say "Not found" -- never guess about the project.
