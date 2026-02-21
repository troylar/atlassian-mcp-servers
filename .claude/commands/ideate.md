---
name: ideate
description: Explore and refine a feature idea before committing to an issue
allowed-tools: Bash, Read, Grep, Glob, Task
---

# /ideate Skill

Have a structured conversation about a feature idea before creating an issue. Explore feasibility, vision alignment, complexity, and alternative approaches — without committing to anything.

## Usage

```
/ideate add OAuth 2.0 support for all servers
/ideate what if we added a webhook listener tool for Bitbucket
/ideate I want to add Jira Service Management tools
```

The argument is a rough idea — it can be vague, ambitious, or half-formed. That's the point.

## Workflow

### Step 1: Understand the Idea

Parse the user's input and restate it back clearly:
- What is the user trying to achieve?
- Which server(s) does this affect?
- What problem does it solve?

Ask clarifying questions if the idea is too vague to evaluate. Keep it to 1-2 targeted questions, not an interrogation.

### Step 2: Vision Check

Read `VISION.md` and evaluate the idea against the product vision.

Check against **"What This Is NOT"** negative guardrails:
- Does this turn a server into a wrapper library?
- Does this create coupling between servers?
- Does this add admin-level operations?
- Does this introduce background processing?
- Does this add a UI layer?

Check against **Out of Scope** (hard no): Atlassian admin APIs, webhook receivers, bulk operations, Marketplace integration, OAuth authorization code flow.

Run the **Litmus Test**:
- Does a typical developer need this operation regularly?
- Does it work with both Cloud and Data Center?
- Is it a single, focused operation?
- Can it be tested without a live Atlassian instance?
- Does it follow existing patterns?

Display the alignment:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🎯 Vision Alignment
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Supports:     <which core principles>
  Guardrails:   ✅ / ⚠️ <any "Is Not" concerns>
  Scope:        ✅ / ❌ <if it hits an out-of-scope area>
  Litmus test:  ✅ / ⚠️ <flag any concerns>

────────────────────────────────────────────
```

Do NOT stop here if there are warnings. This is ideation — explore the tension, don't block on it.

### Step 3: Explore Feasibility (parallel Sonnet agents)

Launch 2 parallel Sonnet agents:

**Agent A — Technical landscape:**
1. Read `CLAUDE.md` and `README.md` for architecture overview
2. Search the codebase for related modules, patterns, and existing infrastructure
3. Identify:
   - What already exists that this idea could build on
   - What would need to be created from scratch
   - Which server(s) and files would be affected
   - Rough complexity: small (1-2 files), medium (3-5 files), large (6+ files)
4. Flag any technical blockers or dependencies

**Agent B — Prior art and alternatives:**
1. Search existing GitHub issues for related ideas: `gh issue list --search "<keywords>" --state all --limit 10`
2. Check if similar features exist in the current codebase but are undiscovered
3. Think about simpler alternatives that achieve 80% of the goal with 20% of the effort

### Step 4: Present the Analysis

Display a structured analysis:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  💡 Ideation: <idea summary>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📐 Feasibility
  Complexity:     Small / Medium / Large
  Server(s):      <which servers affected>
  Builds on:      <existing modules/patterns>
  New code:       <what would be created>
  Blockers:       <any technical blockers, or "none">

🔗 Related
  Existing issues: <list any related issues, or "none found">
  Existing code:   <anything already in the codebase that helps>

💡 Approaches
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  A) <Lean approach>
     Complexity: <Small/Medium>
     Trade-offs: <what you give up>
     Vision fit: ✅ / ⚠️

  B) <Full approach>
     Complexity: <Medium/Large>
     Trade-offs: <what you gain vs. cost>
     Vision fit: ✅ / ⚠️

  C) <Alternative framing> (if applicable)
     What if instead of <X> we did <Y>?
     Complexity: <Small/Medium>
     Vision fit: ✅ / ⚠️

────────────────────────────────────────────
```

Always present at least 2 approaches:
- **A lean version** that could ship quickly with minimal complexity
- **A fuller version** that's more complete but more complex

### Step 5: Open Discussion

After presenting the analysis, invite the user to discuss:

```
────────────────────────────────────────────
  🗣️ What do you think?

  Options:
    → Discuss further — ask questions, refine the idea
    → Pick an approach — I'll draft as /new-issue
    → Park it — save the idea for later
    → Drop it — this isn't the right direction

────────────────────────────────────────────
```

### Step 6: Resolution

Based on the user's decision:

**If "Pick an approach":**
- Confirm which approach they chose
- Ask if they want to create the issue now: "Ready for `/new-issue`?"

**If "Park it":**
- Suggest creating a GitHub issue labeled `idea` or `discussion` to capture the analysis

**If "Drop it":**
- Acknowledge and move on. No issue created.

## Guidelines

- This is a **safe space for ideas** — don't shut things down, explore them
- Always present alternatives, even for well-aligned ideas
- Vision warnings are discussion points, not stop signs
- Be honest about complexity — don't undersell or oversell
- Keep the tone collaborative — "here's what I found" not "this won't work"
