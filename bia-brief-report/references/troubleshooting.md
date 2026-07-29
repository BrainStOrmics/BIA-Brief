# Troubleshooting

- Missing `bia-brief`: install the pinned release before retrying.
- Missing model config: request a local configuration path; never ask the user
  to paste an API key into chat.
- Missing figures: stop and ask for the correct project directory.
- PDF export failure: verify Playwright Chromium with `playwright install chromium`.
- Interactive review pause: retain the same process and follow the prompt, or
  use the configured automatic approval mode for unattended batch runs.
