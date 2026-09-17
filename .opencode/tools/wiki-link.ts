import { tool } from "@opencode-ai/plugin"

export default tool({
  description: "Analyze wiki link graph: find orphans, broken links, and suggest cross-references",
  args: {
    action: tool.schema
      .enum(["orphans", "broken", "stats", "all"])
      .describe("Analysis type: orphans (no inbound links), broken (dead wikilinks), stats (link counts), all"),
  },
  async execute(args, context) {
    const { action } = args
    const worktree = context.worktree
    const wikiRoot = `${worktree}/wiki`

    const wikilinkRegex = /\[\[([^\]|]+)(?:\|[^\]]+)?\]\]/g
    const allPages: string[] = []
    const inboundLinks: Record<string, number> = {}
    const outboundLinks: Record<string, string[]> = {}
    const brokenLinks: Array<{ page: string; target: string; line: number }> = []

    const scanPages = async () => {
      const entries = await Array.fromAsync(new Bun.Glob("**/*.md").scan({ cwd: wikiRoot, absolute: true }))
      const pageSet = new Set<string>()

      for (const file of entries) {
        const relative = file.replace(wikiRoot + "/", "").replace(/\.md$/, "")
        pageSet.add(relative)
        allPages.push(relative)
        outboundLinks[relative] = []
      }

      for (const file of entries) {
        const relative = file.replace(wikiRoot + "/", "").replace(/\.md$/, "")
        const content = await Bun.file(file).text()
        const lines = content.split("\n")

        let match: RegExpExecArray | null
        for (let i = 0; i < lines.length; i++) {
          wikilinkRegex.lastIndex = 0
          while ((match = wikilinkRegex.exec(lines[i])) !== null) {
            const target = match[1].trim()
            outboundLinks[relative].push(target)
            if (!inboundLinks[target]) inboundLinks[target] = 0
            inboundLinks[target]++

            if (!pageSet.has(target) && !target.startsWith("http")) {
              brokenLinks.push({ page: relative, target, line: i + 1 })
            }
          }
        }
      }
    }

    await scanPages()

    let output = "## Wiki Link Analysis\n\n"

    if (action === "orphans" || action === "all") {
      const orphans = allPages.filter((p) => !inboundLinks[p] || inboundLinks[p] === 0)
      output += "### Orphan Pages (no inbound links)\n"
      if (orphans.length === 0) {
        output += "None found!\n"
      } else {
        for (const page of orphans) {
          output += `- [[${page}]]\n`
        }
      }
      output += "\n"
    }

    if (action === "broken" || action === "all") {
      output += `### Broken Links (${brokenLinks.length} found)\n`
      if (brokenLinks.length === 0) {
        output += "None found!\n"
      } else {
        for (const bl of brokenLinks) {
          output += `- [[${bl.target}]] referenced in [[${bl.page}]]:${bl.line}\n`
        }
      }
      output += "\n"
    }

    if (action === "stats" || action === "all") {
      const sorted = Object.entries(inboundLinks).sort((a, b) => b[1] - a[1])
      output += "### Link Statistics\n"
      output += `- Total pages: ${allPages.length}\n`
      output += `- Total inbound links: ${Object.values(inboundLinks).reduce((a, b) => a + b, 0)}\n`
      output += `- Pages with inbound links: ${Object.keys(inboundLinks).length}\n`
      output += "\n#### Most Linked Pages\n"
      for (const [page, count] of sorted.slice(0, 10)) {
        output += `- [[${page}]] — ${count} inbound links\n`
      }
      output += "\n#### Suggested Cross-References\n"
      if (brokenLinks.length > 0) {
        const mostMissing = new Map<string, number>()
        for (const bl of brokenLinks) {
          mostMissing.set(bl.target, (mostMissing.get(bl.target) || 0) + 1)
        }
        const sortedMissing = [...mostMissing.entries()].sort((a, b) => b[1] - a[1])
        for (const [target, count] of sortedMissing.slice(0, 5)) {
          output += `- [[${target}]] referenced ${count} times but page doesn't exist — consider creating it\n`
        }
      }
    }

    return output
  },
})
