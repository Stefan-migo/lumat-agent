# PWA Shell Specification

## Purpose

Make the React/Vite panel installable while preserving authenticated online behavior and safe caching.

## Requirements

### Requirement: PWA-1 — Installable Shell

The web app MUST provide valid metadata, unchanged application icons, and service-worker registration sufficient for supported browsers to offer installation over HTTPS. The manifest MUST use `/panel/app/` for its start URL and scope.
(Previously: The manifest and installation paths were not bound to the production `/panel/app/` subtree.)

#### Scenario: App is installable at its production path
- GIVEN a supported browser loads `https://panel.lumat.cl/panel/app/`
- WHEN it reads the manifest
- THEN `start_url` and `scope` are within `/panel/app/` and the existing icons resolve

#### Scenario: Insecure development
- GIVEN the panel is served without HTTPS in local development
- WHEN the app starts
- THEN it remains usable and does not falsely promise installation or push support

### Requirement: PWA-2 — Safe Cache Policy

The service worker MUST cache only the versioned `/panel/app/` shell and public static assets, MUST NOT cache authenticated API responses, and MUST allow a new shell version to replace an old one.
(Previously: Cache and worker URL rules were rooted at `/panel/`.)

#### Scenario: Shell works offline without API leakage
- GIVEN the shell was previously loaded and the browser is offline
- WHEN a user opens a cached `/panel/app/` shell route
- THEN the shell loads from cache, while `/panel/api/` responses are never cached

#### Scenario: Asset update
- GIVEN a new application shell version is deployed
- WHEN the service worker updates
- THEN stale shell assets are replaced without retaining old authenticated data


### Requirement: PWA-3 — Permission Fallback

The panel MUST request push permission only from an explicit user action, MUST explain denied/unsupported states, and MUST keep notification-center and WhatsApp/SMTP fallback usable.

#### Scenario: Permission denied

- GIVEN the user denies browser push permission
- WHEN notification settings render
- THEN the denial is shown and non-push delivery remains available
