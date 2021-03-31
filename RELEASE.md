# Procsim release steps

- Ensure that the software is release-ready.
- If a new major/minor version is needed:
  - Create release branch
  - Create Jenkins release job
- Update the version number in version.py.
- Update CHANGELOG.

- Make a release build in Jenkins.
- Do a 'smoke test' on the package as build by Jenkins.

- Create git tag containing the version.
- Place the package on `<jupiter>/projects/procsim/Deliverables/<delivery subdirectory>` (TBD).
- Distribute to ESA by FTP (TBD).

- Merge changes (if any) from release branch back to master.
