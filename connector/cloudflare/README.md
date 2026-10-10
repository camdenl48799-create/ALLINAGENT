# ALLINAGENT ChatGPT Connector (Cloudflare Workers)

A small, read-only Model Context Protocol (MCP) server that lets a compatible MCP client inspect the **public** `camdenl48799-create/ALLINAGENT` GitHub repository.

## What it does

The initial version exposes five read-only tools:

- `get_project_overview` — reads the README and package version.
- `list_project_files` — lists repository files and folders.
- `read_project_file` — reads a text file from `main`.
- `search_project_code` — searches a bounded set of up to eight small text files.
- `list_project_pull_requests` — lists up to ten open pull requests.

It cannot edit files, create branches, open pull requests, merge code, run shell commands, or access your PC. It only reads the public repository. No AI API key or GitHub token is required for this first version.

## Free local test

You need Node.js/npm. From this folder:

```bash
npm install
npm run typecheck
npm run dev
```

The local MCP endpoint should be `http://localhost:8787/mcp`. The health check is `http://localhost:8787/health`. The root page is only a short status message; use an MCP client to call tools at `/mcp`.

Use the MCP Inspector to test the endpoint if you have it installed. The server uses Cloudflare's `createMcpHandler` and Streamable HTTP transport.

## Deploy to the Cloudflare Workers Free plan

1. Create/sign in to a Cloudflare account and open a terminal in this folder.
2. Run `npm install`.
3. Run `npx wrangler login` and finish Cloudflare's normal sign-in flow.
4. Run `npm run deploy`.
5. Copy the exact deployed hostname, such as `allinagent-chatgpt-connector.YOUR-SUBDOMAIN.workers.dev` (without `https://` or a path).
6. In the Cloudflare Worker settings, add the non-secret environment variable `MCP_ALLOWED_HOST` with that exact hostname, then redeploy.
7. Verify `https://YOUR-HOST/health` returns JSON and configure a compatible MCP client to use `https://YOUR-HOST/mcp`.

Do not paste account passwords, recovery codes, or tokens into chat or commit them to GitHub. The connector is intentionally read-only and doesn't need a GitHub credential. Cloudflare may ask you to complete its standard account setup. Free-tier limits apply; check the current [Workers limits](https://developers.cloudflare.com/workers/platform/limits/) before deployment.

## Add it to ChatGPT

If your ChatGPT account and workspace expose custom MCP connector setup, use the deployed HTTPS MCP URL ending in `/mcp`. ChatGPT plan and workspace restrictions may prevent custom connectors from being added even when the server itself works. See [OpenAI's custom MCP server guide](https://developers.openai.com/api/docs/guides/custom-mcp-server).

## Safety and limitations

- The repository name and default branch are fixed in source code; callers cannot choose arbitrary repositories or hosts.
- All tools are read-only.
- File paths reject traversal segments and block likely environment/credential/key files.
- File reads and search output are capped to avoid large responses.
- Search checks only a bounded set of files and may miss matches.
- The endpoint is intended for public repository data only. Do not add private repository access or write tools without a separate authentication and permission design.
