# GitHub publication checklist — required before public visibility

This ZIP is **technically organized for GitHub**, but public release remains conditional on rights/privacy review and a native smoke run. A local GitHub push cannot be performed from this artifact-generation environment.

## 1. Rights and licensing (human approval required)

- [ ] Decide whether to grant MIT, Apache-2.0, BSD, GPL or another appropriate license to original OpenDSSSim source. **Do not** claim a license until authorized by the copyright holder(s).
- [ ] Review upstream `OpenDSS_License.txt` for each IEEE-123 feeder and source provenance docs for all test feeders (including IEEE-8500 and European LV data).
- [ ] Verify permission to redistribute archived experimental evidence and reference coordinates.
- [ ] Add correct project `LICENSE` and author/copyright notices when approved.

## 2. Privacy and machine-specific paths

- [ ] Search all docs, archived receipts and generated logs for machine names, personal paths, email addresses, tokens and researcher-only metadata.
- [ ] In the supplied source, a small set of original docs/receipts contains local `C:\Users\...` and Dropbox paths. See `docs/release/PRIVATE_PATH_REVIEW.json`. **No original source/evidence bytes have been silently redacted.**
- [ ] Decide whether to keep the source archive full in a private repository, to redact and re-qualify those files for public release, or to omit private evidence from a separate public edition. A public clone cannot revoke previously committed secrets.

## 3. Native and scientific validation

- [ ] Run the offline integrity/test command in `docs/tutorial/05_TESTING_AND_REPRODUCIBILITY.md`.
- [ ] Native smoke-test Lessons 01,02,03,04,05,06,08 on the target Windows/Conda setup.
- [ ] Confirm Gurobi licensing and run Lessons 07,09 (including both slack-first/service-first sensitivity).
- [ ] Run `--paper-campaign --steps 24` if publishing new campaign figures; archive native receipts separately.
- [ ] Verify no direct AltDSS bypass or frozen simulator changes in contributed controller scripts.
- [ ] Compare any new scientific claims with existing qualified RBC/MPC and original source contracts.

## 4. Initial push (manually, from a folder extracted from the release ZIP)

```powershell
cd OpenDSSSim
python scripts/verify_release.py
# Review privacy and license checklist *before* the next step.
git init
git branch -M main
git add .
git status --short
git commit -m "Initial OpenDSSSim release with IEEE-123 course"
# Create an EMPTY repository on GitHub, then copy its exact URL:
git remote add origin https://github.com/<OWNER>/<REPOSITORY>.git
git push -u origin main
```

Replace `<OWNER>/<REPOSITORY>` with your actual GitHub destination. **Do not** paste a token into a script or commit. You may use GitHub CLI/credential manager for authentication. Push privately first until the required checks are closed.

## 5. Suggested branch/review discipline

Protect `main`, use PRs for controller features, require offline checks, and treat any change under `src/opendsssim/{plant,backends,environment,problem,runtime,semantics,persistence}/` as a separately justified simulator change. Keep controller-specific improvements in `controllers/` or `examples/` and preserve source manifests and evidence.
