# Releasing

1. Update `VERSION` file with the `webrtc-sdk/webrtc` commit to use and version number.
2. Tag the release: `git tag m<version number>`
  * The m prefix is required for the CI.
3. Push changes: `git push --tags`
4. Wait for CI to build and release.
5. Verify release is completed.
