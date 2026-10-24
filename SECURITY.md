# Security policy

## Supported versions

Only the latest release receives fixes. Please check that the problem still happens there.

## What the app does (and does not do)

Duplicate Finder is an offline desktop app: it has no server, no account and no network access of
its own. It reads the folders the user chooses and, only when the user confirms, moves files to a
quarantine folder. The data it saves (settings, operation history and an error log) stays in
`%APPDATA%\BuscadorDuplicados`.

Problems that matter here include, for example: a way to make the app delete, overwrite or move
files the user did not ask about; a path that escapes the chosen folders; or code execution
through a crafted file name or image.

## Reporting a vulnerability

Please **do not open a public issue** for a vulnerability. Use GitHub's private report instead:
open the **Security** tab of the repository and choose **Report a vulnerability**.

Please include the version, the steps to reproduce it and what you expected to happen. You will
get an answer as soon as possible; this is a personal project, so there is no guaranteed response
time. Once a fix is released the report can be made public, and you will be credited if you wish.

For problems that are not security related (a bug, an idea), use the
[issue templates](https://github.com/Sayessol/buscador-de-duplicados/issues/new/choose).
