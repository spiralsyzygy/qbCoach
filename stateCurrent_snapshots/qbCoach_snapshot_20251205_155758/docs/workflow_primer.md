# qbCoach Development Workflow Primer

## Three Roles

### **1. Matthew (Human Developer)**
- Decides the next feature.
- Runs tests in VS Code.
- Manages branches, commits, snapshots.
- Passes focused tasks to Codex.
- Brings architectural questions to ChatGPT.

### **2. Codex (Repo Mechanic)**
- Edits real files in the repo.
- Follows clear modular prompts.
- Writes/refactors Python code + tests.
- Applies deterministic logic exactly as specified.
- Does NOT invent rules or card data.

### **3. ChatGPT (Architect + Roadmap Brain)**
- Designs clean, deterministic subsystems.
- Maintains the roadmap doc.
- Reviews Codex output and test failures.
- Produces Codex-ready instructions.
- Ensures rules correctness & engine safety.

---

## Development Loop

1. **Define a feature** here with ChatGPT.  
2. ChatGPT produces an architectural spec + Codex prompt.  
3. Paste the prompt into Codex → Codex modifies code.  
4. Run tests in VS Code Test Panel.  
5. Return results here → ChatGPT validates + updates roadmap.  
6. Commit passing code → move to next feature.

---

## Efficiency Guidelines

- Keep long docs in `/docs/` instead of chat or canvas.
- Reset the chat after 1–2 major features.
- Use pytest test panel for rapid iteration.
- Let Codex handle file edits; ChatGPT handles architecture.
- Store snapshots of the repo after each stable milestone.

