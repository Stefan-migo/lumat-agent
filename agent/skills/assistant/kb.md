# Knowledge base

Use `kb.retrieve` for questions about Lumat: policies, prices, service details, and
gasfiteria know-how the corpus covers.

## Usage

- `kb.retrieve` takes `query` (the user's question, not your own keywords) and an
  optional `top_k` (1–5, default 5). Rank the results and cite what you use.
- The assistant is internal and reads the whole corpus, including internal documents.

## Gotchas

- Ground the answer in retrieved results; do not invent policy, prices, or procedure.
- If the retrieval returns nothing usable, say so and ask for the detail you need
  instead of guessing.
- For one customer's history use the customer tools, not the knowledge base.
