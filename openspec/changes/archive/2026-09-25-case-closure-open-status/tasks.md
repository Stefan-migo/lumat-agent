# Tasks: Case Closure and Open-Status Projection

- [x] **T1** — Route every production `Case.status` write through
  `app/services/cases.py::_apply_status` and cover classification/emergency
  reactivation with integration tests.
- [x] **T2** — Verify the focused and full test suites.
- [x] **T3** — Archive this change, syncing the `AD-HOY-1` delta into the live
  `advanced-dashboards` specification.
