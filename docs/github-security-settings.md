# GitHub repository security settings

These are publication-time repository settings, not substitutes for files committed in this repository.

## Required before the repository is considered public-ready

1. Make the repository public only after the pre-public secret/privacy scan is complete.
2. Enable GitHub **CodeQL default setup** for Python rather than maintaining a redundant advanced CodeQL workflow unless default setup proves insufficient.
3. Enable secret scanning and push protection where the account/repository plan exposes them.
4. Enable Dependabot alerts and security updates.
5. Enable private vulnerability reporting so `SECURITY.md` has a working confidential channel.
6. Create a default-branch ruleset that, at minimum:
   - requires pull requests for normal changes once collaboration begins;
   - requires the relevant CI status checks;
   - blocks force pushes and branch deletion;
   - requires code-scanning results when available.
7. Keep the default `GITHUB_TOKEN` permission read-only unless a workflow explicitly needs a narrow write permission.
8. Review every Actions dependency update before changing a pinned commit SHA.
9. After the release process is mature, consider immutable releases for published versions.

## Repository metadata

Before publication, set a concise repository description, topics, social preview, license recognition and project website/docs link if one exists. Do not advertise unsupported platforms or stability levels.

## OWNER/REPOSITORY placeholder

`.github/ISSUE_TEMPLATE/config.yml` contains an intentional `OWNER/REPOSITORY` placeholder for the private-vulnerability-reporting URL. Replace it only after the final GitHub repository identity is known; `scripts/check_public_repo.py --publication` must fail while this placeholder remains.
