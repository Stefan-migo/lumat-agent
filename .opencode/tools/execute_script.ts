import { tool } from "@opencode-ai/plugin"

export default tool({
  description: "Execute TypeScript/JavaScript code in a Node.js sandbox for multi-step logic, prototyping, or validation",
  args: {
    code: tool.schema.string().describe("TypeScript or JavaScript code to execute"),
    timeout: tool.schema.number().optional().describe("Timeout in milliseconds (default: 30000)"),
  },
  async execute(args, _context) {
    const { code, timeout = 30000 } = args
    const tmpDir = `/tmp/opencode/sandbox-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`

    try {
      await Bun.$`mkdir -p ${tmpDir}`
      const filePath = `${tmpDir}/script.ts`
      await Bun.write(filePath, code)
      const result = await Bun.$`npx tsx ${filePath}`.timeout(timeout).text()
      return result.trim() || "Script executed successfully (no output)"
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err)
      return `Error: ${message}`
    } finally {
      await Bun.$`rm -rf ${tmpDir}`.nothrow()
    }
  },
})
