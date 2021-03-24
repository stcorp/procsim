# Procsim release steps

- Ensure that the software is release-ready.

- Update the version number in version.py.
- Update CHANGELOG.

- Make a release build in Jenkins.
- Do a 'smoke test' on the package as build by Jenkins: extract it and run procsim.py.

- Create git tag containing the version.
- Place the package on `<jupiter>/projects/procsim/Deliverables/<delivery subdirectory>` (TBD).
- Distribute to ESA by FTP (TBD).
