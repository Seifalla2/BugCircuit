# Publish BugCircuit to GitHub

First, create an **empty public repository** named `BugCircuit` on GitHub under your own account. Do not initialize it with README, license or `.gitignore` because those files are already included.

In the extracted project directory:

```bash
git init
git branch -M main
git add .
git commit -m "feat: initial evidence-first BugCircuit v0.1 alpha"
git remote add origin https://github.com/Seifalla2/BugCircuit.git
git push -u origin main
```

GitHub requires the user to authenticate for pushing. You may need to configure `git config user.name` and `git config user.email` locally before committing. The public URL is **not live until these steps succeed**.

After pushing:
1. Confirm repository visibility is Public and check Actions → Tests results.
2. Inspect the README rendered on GitHub and check the link targets.
3. Run the sample offline command locally and review generated HTML/JSON output.
4. Optionally create a `v0.1.0-alpha` GitHub Release after CI passes.
5. Do not add private project HAR recordings, credentials or secrets to issues/commits.

The bundled `.github/workflows/test.yml` runs tests on Python 3.10/3.12/3.13 and a Ruff lint step. It is not enabled until you publish the repository.
