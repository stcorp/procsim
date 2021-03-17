# Procsim release steps

- Ensure that the software is release-ready.

- Update README.md.
    - Version numbers, release date, etc.
    - Update changelog and known issues.

- Update the version number in Jenkins (the release package is build using `build.sh <version>`).

- Verify that the package builds properly and the tests are performed as expected in Jenkins.

- Do a smoke test on the package as build by Jenkins.

- Create git tag containing the version.

- Place the package on `<jupiter>/projects/procsim/Deliverables/<delivery subdirectory>` (TBD).

- Distribute to ESA by FTP (TBD).
