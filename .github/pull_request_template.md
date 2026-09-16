## Problem

Describe the defect class or user problem this changes.

## Change

Describe the architectural boundary changed and why this is the smallest correct scope.

## Evidence

- [ ] Relevant regression test added/updated
- [ ] `python scripts/check_release_tree.py` passes
- [ ] `python scripts/check_public_repo.py` passes
- [ ] Progress/control/UI contracts pass where relevant
- [ ] Real FFmpeg smoke/E2E run where relevant
- [ ] Packaging/reproducibility checks run where relevant

## Risk / rollback

Describe failure modes, migrations, persistence changes, compatibility risk and rollback behavior.

## Public-release checks

- [ ] No credentials, private paths, private media, logs or user data added
- [ ] New dependencies/downloads have provenance + license review
- [ ] User-visible behavior/docs updated
- [ ] Tests were not weakened merely to make the change pass
