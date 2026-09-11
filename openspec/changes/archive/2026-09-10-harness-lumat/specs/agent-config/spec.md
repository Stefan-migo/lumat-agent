# Delta for agent-config

## MODIFIED Requirements

### Requirement: AC-6 — Skills as Reference Files

The system MUST ship `agent/skills/*.md` as declarative, non-executable references and MUST NOT load skill content into an LLM prompt. Runtime assistant behavior MUST use validated persona, prompt, and registry configuration read-only. The configuration terminology MUST call Lumat’s former “SDB (Deterministic Behavior Database)” surface “Gates deterministas / Guardrails”; the implementation MUST inventory all repository consumers before changing references.
(Previously: skills were reference-only and deterministic gates were described as the authoritative SDB.)

#### Scenario: Skill never loaded

- GIVEN a panel conversation runs end-to-end
- WHEN runtime prompts are assembled
- THEN no `agent/skills/` content appears in any LLM prompt

#### Scenario: Runtime configuration is read-only

- GIVEN validated assistant persona, prompts, and registry data
- WHEN a panel turn runs
- THEN the harness consumes that configuration without editing or executing it

### Requirement: AC-9 — Assistant Runtime Configuration

The system MUST provide existence-validated assistant registry, personas, prompts, and declared tool capabilities under `agent/` for read-only runtime consumption. Startup MUST fail clearly for missing references, while reference-only skills remain non-executable.
(Previously: configuration was validated and exposed to consumers, but the panel harness did not consume its assistant persona and prompt set.)

#### Scenario: Complete configuration loads

- GIVEN registry entries reference existing personas, prompts, and declared tools
- WHEN configuration loads for a panel turn
- THEN the validated read-only assistant configuration is available to the harness

#### Scenario: Missing runtime reference

- GIVEN a required persona or prompt reference is missing
- WHEN configuration loads
- THEN validation reports the missing reference and prevents an invalid assistant from starting
