# Archive Report: Case Closure and Open-Status Projection

## Final state

Delivered to `main` through PR #365, merge commit `33f1feba`.

The native review receipt has lineage `review-b2c7c2f6145c0c7b`, risk `medium`, and lens `review-reliability`. It was approved with zero findings; authority was burned. The consumed revision was `sha256:b5c56310e528449f7b019565d908f010732780933e6b44acd93cf4bccde036ca`.

Verification completed with the full suite at 1466 passed and 2 warnings. The CI `test` job passed in 2m20s.

This archive syncs the `AD-HOY-1` delta: urgent cases are those flagged by `escalated_at` or `emergency` that are still open by status, including NULL status and excluding `closed`, `cerrado`, `finalizado`, and `cancelado`. The live specification remained unchanged until this archive sync.

Writer centralization covers classification and emergency, so every `Case.status` write goes through `_apply_status`.
