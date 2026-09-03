# PWA Shell Specification

## Purpose

Make the React/Vite panel installable while preserving authenticated online behavior and safe caching.

## Requirements

### Requirement: PWA-1 — Installable Shell

The web app MUST provide a valid manifest, application icons, and service-worker registration sufficient for supported browsers to offer installation over HTTPS.

#### Scenario: Manifest is valid

- GIVEN a supported browser loads the panel over HTTPS
- WHEN it reads the application metadata
- THEN the manifest and required icons identify an installable application

#### Scenario: Insecure development

- GIVEN the panel is served without HTTPS in local development
- WHEN the app starts
- THEN it remains usable and does not falsely promise installation or push support

### Requirement: PWA-2 — Safe Cache Policy

The service worker MUST cache only the versioned application shell and public static assets, MUST NOT cache authenticated API responses, and MUST allow a new shell version to replace an old one.

#### Scenario: API data is never cached

- GIVEN an authenticated API request
- WHEN the service worker handles it
- THEN the response is fetched according to the online session and is not stored in the shell cache

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
