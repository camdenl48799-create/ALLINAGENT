# ALLINAGENT Browser Workspace

This is a static HTML/CSS/JavaScript workspace foundation. It has no build step and no third-party runtime dependencies.

## Open it

Open `web/index.html` in a modern browser, or serve the repository with any static file server and navigate to `/web/`.

## Current capabilities

- Create, view, and delete draft conversations.
- Drafts use a namespaced browser `localStorage` key.
- The layout includes basic keyboard focus indicators, semantic navigation, and a narrow-screen layout.

## Important limits

- Drafts remain in this browser profile; they do not sync across devices or accounts.
- This page cannot read or write the Python CLI's local workspace files.
- No cloud AI, account system, server, or network transmission is implemented.
- Clearing browser site data may remove drafts. Browser storage can be disabled or full.
- Do not put passwords, API keys, or other secrets into browser drafts.
- Inspect any data before sharing it. Exported CLI JSON may contain user-authored text.
