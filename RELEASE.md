# Procsim release steps

- Ensure that the software is release-ready.
- If a new major or minor version is needed:
  - Create release branch, named `release_<major>.<minor>.x`
  - Create Jenkins release job
- Update the version number in version.py.
- For new plugin, add procsim/plugin dir to packages in setup.py.
- Update CHANGELOG.
- Make a release build in Jenkins.
- Do a 'smoke test' on the package as build by Jenkins.
- Create git tag containing the version.
- Merge changes (if any) from release branch back to master.
