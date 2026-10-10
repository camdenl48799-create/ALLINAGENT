import { createMcpHandler } from "agents/mcp/server";
import { McpServer } from "@modelcontextprotocol/server";
import { z } from "zod";

interface Env {
  /** Exact hostname serving this Worker, without scheme or port. */
  MCP_ALLOWED_HOST?: string;
}

const OWNER = "camdenl48799-create";
const REPO = "ALLINAGENT";
const BRANCH = "main";
const API_ROOT = `https://api.github.com/repos/${OWNER}/${REPO}`;
const RAW_ROOT = `https://raw.githubusercontent.com/${OWNER}/${REPO}/${BRANCH}`;
const MAX_FILE_CHARS = 18_000;
const MAX_DIRECTORY_ENTRIES = 50;
const MAX_SEARCH_FILES = 8;

function safePath(input: string): string {
  const path = input.trim().replace(/^\/+|\/+$/g, "");
  if (!path) return "";
  const parts = path.split("/");
  if (parts.some((part) => !part || part === "." || part === "..")) {
    throw new Error("Invalid repository path.");
  }
  if (parts.some((part) => /^(\.env($|\.)|.*\.(pem|key)$)/i.test(part)
    || /secret|credential/i.test(part))) {
    throw new Error("That path is blocked by the connector's safety filter.");
  }
  return path;
}

function encodePath(path: string): string {
  return path.split("/").map(encodeURIComponent).join("/");
}

async function githubJson<T>(url: string): Promise<T> {
  const response = await fetch(url, {
    headers: {
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "ALLINAGENT-ChatGPT-Connector",
    },
  });
  if (!response.ok) {
    if (response.status === 403 || response.status === 429) {
      throw new Error("GitHub rate limit reached. Please wait and try again.");
    }
    if (response.status === 404) {
      throw new Error("GitHub resource not found in the public ALLINAGENT repository.");
    }
    throw new Error(`GitHub request failed with HTTP ${response.status}.`);
  }
  return response.json() as Promise<T>;
}

async function rawText(path: string): Promise<string> {
  const response = await fetch(`${RAW_ROOT}/${encodePath(path)}`, {
    headers: { "User-Agent": "ALLINAGENT-ChatGPT-Connector" },
  });
  if (!response.ok) {
    if (response.status === 404) throw new Error(`File not found: ${path}`);
    throw new Error(`Could not read file (HTTP ${response.status}).`);
  }
  return response.text();
}

function textResult(value: unknown) {
  return {
    content: [{ type: "text" as const, text: JSON.stringify(value, null, 2) }],
  };
}

function createServer() {
  const server = new McpServer({
    name: "ALLINAGENT GitHub Connector",
    version: "0.1.0",
  });

  server.registerTool(
    "get_project_overview",
    {
      description: "Read the public ALLINAGENT README and package version. This tool is read-only.",
      inputSchema: {},
    },
    async () => {
      const [readme, pyproject] = await Promise.all([
        rawText("README.md"),
        rawText("pyproject.toml"),
      ]);
      const version = pyproject.match(/^version\s*=\s*"([^"]+)"/m)?.[1] ?? "unknown";
      const release = readme.match(/\*\*v([^*]+?)\s+—\s+Current release\*\*/i)?.[1]?.trim() ?? "not stated";
      return textResult({
        repository: `${OWNER}/${REPO}`,
        defaultBranch: BRANCH,
        packageVersion: version,
        readmeReleaseLabel: release,
        readmeExcerpt: readme.slice(0, 5_000),
        note: "The repository is public. This connector does not run ALLINAGENT or access the user's PC.",
      });
    },
  );

  server.registerTool(
    "list_project_files",
    {
      description: "List files and folders in the public ALLINAGENT repository. Optional path is relative to the repository root. Results are capped at 50 entries.",
      inputSchema: { path: z.string().optional() },
    },
    async ({ path }) => {
      const cleanPath = safePath(path ?? "");
      const url = cleanPath
        ? `${API_ROOT}/contents/${encodePath(cleanPath)}?ref=${BRANCH}`
        : `${API_ROOT}/contents?ref=${BRANCH}`;
      const data = await githubJson<Array<{ name: string; path: string; type: string; size?: number; html_url?: string }> | { message?: string }>(url);
      if (!Array.isArray(data)) {
        throw new Error("That path is not a directory.");
      }
      return textResult({
        repository: `${OWNER}/${REPO}`,
        path: cleanPath || "/",
        truncated: data.length > MAX_DIRECTORY_ENTRIES,
        entries: data.slice(0, MAX_DIRECTORY_ENTRIES).map((item) => ({
          name: item.name,
          path: item.path,
          type: item.type,
          size: item.size ?? null,
          url: item.html_url ?? null,
        })),
      });
    },
  );

  server.registerTool(
    "read_project_file",
    {
      description: "Read a text file from the public ALLINAGENT repository's main branch. Blocks likely secret/key files and truncates long output.",
      inputSchema: { path: z.string().min(1).max(300) },
    },
    async ({ path }) => {
      const cleanPath = safePath(path);
      if (!cleanPath) throw new Error("A file path is required.");
      const content = await rawText(cleanPath);
      return textResult({
        path: cleanPath,
        branch: BRANCH,
        truncated: content.length > MAX_FILE_CHARS,
        content: content.slice(0, MAX_FILE_CHARS),
      });
    },
  );

  server.registerTool(
    "search_project_code",
    {
      description: "Search text in up to 8 small source/documentation files from the public ALLINAGENT repository. Returns matching snippets; this bounded search may not scan every file.",
      inputSchema: { query: z.string().trim().min(1).max(60) },
    },
    async ({ query }) => {
      const tree = await githubJson<{ tree?: Array<{ path: string; type: string; size?: number }> }>(
        `${API_ROOT}/git/trees/${BRANCH}?recursive=1`,
      );
      const candidates = (tree.tree ?? [])
        .filter((item) => item.type === "blob" && (item.size ?? 0) <= 60_000)
        .filter((item) => /\.(py|md|toml|json|ya?ml|ts|tsx|js|jsx|txt)$/i.test(item.path))
        .filter((item) => !/(^|\/)(\.env[^/]*|.*secret.*|.*credential.*|.*\.(pem|key))$/i.test(item.path))
        .slice(0, MAX_SEARCH_FILES);
      const needle = query.toLowerCase();
      const matches: Array<{ path: string; line: number; snippet: string }> = [];
      let scanned = 0;
      for (const item of candidates) {
        let content: string;
        try {
          content = await rawText(item.path);
        } catch {
          continue;
        }
        scanned += 1;
        const lines = content.split(/\r?\n/);
        for (let i = 0; i < lines.length; i += 1) {
          if (lines[i].toLowerCase().includes(needle)) {
            matches.push({ path: item.path, line: i + 1, snippet: lines[i].slice(0, 220) });
            if (matches.length >= 25) break;
          }
        }
        if (matches.length >= 25) break;
      }
      return textResult({
        query,
        scannedFiles: scanned,
        candidateFileLimit: MAX_SEARCH_FILES,
        matches,
        note: "This is a bounded search over a small set of text files, not a complete repository-wide index.",
      });
    },
  );

  server.registerTool(
    "list_project_pull_requests",
    {
      description: "List up to 10 currently open pull requests for ALLINAGENT. Read-only.",
      inputSchema: {},
    },
    async () => {
      const prs = await githubJson<Array<{
        number: number;
        title: string;
        state: string;
        draft: boolean;
        html_url: string;
        head: { ref: string };
        base: { ref: string };
        updated_at: string;
      }>>(`${API_ROOT}/pulls?state=open&per_page=10`);
      return textResult({
        repository: `${OWNER}/${REPO}`,
        pullRequests: prs.map((pr) => ({
          number: pr.number,
          title: pr.title,
          state: pr.state,
          draft: pr.draft,
          headBranch: pr.head.ref,
          baseBranch: pr.base.ref,
          updatedAt: pr.updated_at,
          url: pr.html_url,
        })),
      });
    },
  );

  return server;
}

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === "/health" && request.method === "GET") {
      return Response.json({
        service: "ALLINAGENT GitHub Connector",
        version: "0.1.0",
        status: "ok",
        toolsAreReadOnly: true,
      });
    }

    if (url.pathname !== "/mcp") {
      return new Response("ALLINAGENT connector. MCP endpoint: /mcp; health: /health\n", {
        status: url.pathname === "/" ? 200 : 404,
        headers: { "Content-Type": "text/plain; charset=utf-8" },
      });
    }

    const configuredHost = env.MCP_ALLOWED_HOST?.trim().toLowerCase();
    const localHosts = ["localhost", "127.0.0.1"];
    const allowedHostnames = configuredHost ? [configuredHost] : localHosts;
    if (!allowedHostnames.includes(url.hostname.toLowerCase())) {
      return Response.json(
        { error: "Set MCP_ALLOWED_HOST to this Worker hostname before accepting remote MCP requests." },
        { status: 503 },
      );
    }

    return createMcpHandler(createServer, { allowedHostnames })(request, env, ctx);
  },
};
