# Civicomfy 2.0 — Development Roadmap

> Scope: only `paperbackwalnut/Civicomfy`, development branch `development/civicomfy-2`. Do not write upstream, and do not merge to main without review.
> Baseline: `555e984bbcb02fc955075cb8eb699a6884c51239`.
> Status legend: [x] completed, [ ] pending. Each item requires tests or manual verification before closure.

## Phase 0: Engineering baseline
- [x] Establish isolated development branch.
- [x] Record implementation plan and guardrails.
- [ ] Add automated CI and Python unit tests with mock ComfyUI services.
- [ ] Add dependency declarations and supported ComfyUI/Python compatibility matrix.
- [ ] Establish representative performance and regression fixtures.

## Phase 1: Safety and integrity — required before production use
- [ ] Restrict root/directory creation to explicitly approved paths; canonicalize symlinks; read-only listing.
- [ ] Replace untrusted HTML interpolation with safe DOM creation or HTML sanitation.
- [ ] Stop persisting API tokens in browser cookies or download history; migrate/redact existing records.
- [ ] Download to isolated temporary paths; atomic finalization; never delete existing valid models.
- [ ] Verify file length and Civitai-provided SHA256 or BLAKE3; fail closed.
- [ ] Implement consistent parameter validation, errors, and logging with secret redaction.

## Phase 2: Civitai search modernization
- [x] Introduce live enum-backed base-model catalog with bounded caching and fallback.
- [ ] Validate API response shapes and Civitai enum naming (including Krea 2, ZImageTurbo, Anima).
- [ ] Prefer official models API; support cursor pagination, sort, period, creator, tags and model types.
- [ ] Add multi-select, searchable base-model/type filters and saved filter preferences.
- [ ] Evaluate direct Meilisearch as optional fallback only; remove hardcoded bearer token.
- [ ] Validate filtering for age/content settings, missing metadata and inaccessible models.

## Phase 3: Reliable downloader
- [ ] Explicit persistent state machine (queued/resolving/downloading/paused/verifying/installed/error).
- [ ] Pause/resume across process restarts with validators and safe partial files.
- [ ] Handle redirect, authentication, rate-limit, Retry-After, HTTP range and expired download URLs.
- [ ] Adaptive per-file concurrency benchmark (1/4/8), bounded global concurrency, speed cap.
- [ ] Push progress events over ComfyUI transport with polling fallback.
- [ ] Download preflight and actionable errors.

## Phase 4: Local model intelligence
- [ ] SQLite index of ComfyUI registered model roots and metadata.
- [ ] Incremental background hashing with pause/throttle and safe network-share handling.
- [ ] Civitai hash identification and batched model/version lookup.
- [ ] Installed, duplicate, newer/different-version display and exact matching.
- [ ] Model destination validation and custom routing rules.

## Phase 5: Native ComfyUI UI
- [ ] Native sidebar entry/commands/settings and accessible detailed preview.
- [ ] Full model detail/versions/files/trained words/license/scan results and preview gallery.
- [ ] Download queue, resume, retry, clear and diagnostics.
- [ ] State separation, DOM safety and UI test coverage.
- [ ] Responsive layout for narrow sidebar and large panels.

## Phase 6: Civitai workflow discovery and import
- [x] Add workflow search API, configured workflow destination and JSON-only download endpoints (backend, experimental).
- [x] Wire an initial workflow browser tab and directory controls into existing Civicomfy modal (unverified in running ComfyUI).
- [ ] Support safely resolved Civitai CDN redirects with no token leakage and validate actual Civitai workflow file formats.
- [ ] Verify downloaded workflow compatibility; provide explicit missing-node/model warnings.
- [ ] Add endpoint tests for invalid JSON, oversized downloads, path safety, duplicate files and redirects.

## Phase 7: Optional advanced features
- [ ] Workflow missing-model detector with reliable identifiers and user confirmation.
- [ ] Saved searches, local bookmarks and optionally authenticated favorites.
- [ ] Opt-in version notifications; no silent deletion/replacement.

## Required delivery gates
1. Each change lives on `development/civicomfy-2` and can be compared against fork `main`.
2. Unit tests for path escape, symlink escape, malicious HTML, secrets, partial/mismatched downloads, concurrent jobs and cancellation.
3. Test against Windows drive/shared model paths, Linux, and ComfyUI portable installs.
4. No upstream GitHub mutations; no publishing workflow triggered by this development branch.
5. Only mark functionality complete when checked by tests or explicitly reported as unverified.
