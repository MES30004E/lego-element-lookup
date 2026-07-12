# Security

Report suspected vulnerabilities privately through GitHub's security advisory feature. Do not include API keys, configuration files, cached inventories, or other personal data in an issue.

LEGO Element Lookup stores desktop API keys through the operating system keychain. Environment variables and legacy local configuration remain supported by the CLI. API keys are used only in HTTPS requests to Rebrickable and are never intentionally logged or bundled.

Desktop beta builds may be unsigned. Verify the SHA-256 checksum published with each GitHub Release and follow the per-application approval instructions in the README. Never disable platform security controls globally.
