import { tool } from "@opencode-ai/plugin"

export default tool({
  description: "Search wiki markdown files with relevance ranking",
  args: {
    query: tool.schema.string().describe("Search query string"),
    maxResults: tool.schema.number().optional().describe("Maximum results to return (default: 10)"),
  },
  async execute(args, context) {
    const { query, maxResults = 10 } = args
    const worktree = context.worktree

    const results: Array<{ file: string; line: number; content: string; relevance: number }> = []
    const terms = query.toLowerCase().split(/\s+/)
    const wikiRoot = `${worktree}/wiki`

    const processDirectory = async (dir: string) => {
      const entries = await Array.fromAsync(new Bun.Glob("**/*.md").scan({ cwd: dir, absolute: true }))
      for (const file of entries) {
        const content = await Bun.file(file).text()
        const lines = content.split("\n")
        let matchCount = 0
        const matchedLines: Array<{ line: number; content: string }> = []

        for (let i = 0; i < lines.length; i++) {
          const lower = lines[i].toLowerCase()
          const lineTerms = terms.filter((t) => lower.includes(t))
          if (lineTerms.length > 0) {
            matchCount += lineTerms.length
            if (matchedLines.length < 3) {
              matchedLines.push({ line: i + 1, content: lines[i].trim().substring(0, 120) })
            }
          }
        }

        if (matchCount > 0) {
          const relativePath = file.replace(worktree + "/", "")
          const title = lines.find((l) => l.startsWith("# "))?.replace("# ", "") || relativePath
          results.push({
            file: relativePath,
            line: matchedLines[0]?.line || 1,
            content: title,
            relevance: matchCount + (title.toLowerCase().includes(query.toLowerCase()) ? 5 : 0),
          })
        }
      }
    }

    await processDirectory(wikiRoot)

    results.sort((a, b) => b.relevance - a.relevance)
    const top = results.slice(0, maxResults)

    if (top.length === 0) return `No results found for "${query}" in wiki/`

    let output = `## Wiki Search Results: "${query}"\n\n`
    for (const r of top) {
      output += `- **${r.content}** — ${r.file}:${r.line} (score: ${r.relevance})\n`
    }
    output += `\nFound ${results.length} results, showing top ${top.length}.`
    return output
  },
})
