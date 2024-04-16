# Procsim release steps

- Ensure that the software is release-ready.
- If a new major or minor version is needed:
  - Create release branch, named `release_<major>.<minor>.x`
- Update the version number in version.py.
- For new plugin, add procsim/plugin dir to packages in setup.py.
- Update CHANGELOG.
- Make a local installation package using the `./build.sh` script
- Do a 'smoke test' on the package
- Create and push a git tag containing the version (e.g., `git tag 2.1.0; git push origin 2.1.0`).
- Merge changes (if any) from release branch back to master.
