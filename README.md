# D&D Encounter Tracker

A Flask REST API + minimal web UI for running D&D combat encounters: add
combatants, track initiative order, apply damage/healing, and advance turns.

Built for ITM 350 Final Project - demonstrates Git branching, automated
testing, containerization, CI/CD, and Infrastructure as Code.

## Architecture

- `app/encounter.py` - pure Python combat logic (no framework dependency)
- `app/api.py` - Flask routes wrapping the logic above
- `app/static/index.html` - single-page UI
- `tests/unit/` - tests against `encounter.py` directly
- `tests/integration/` - tests against the Flask API via test client
- `infra/` - Terraform: EC2 instance + Elastic IP + Security Group
- `.github/workflows/build.yml` - test, build image, push to Docker Hub
- `.github/workflows/release.yml` - Terraform apply, no manual AWS login

## Running locally

```bash
pip install -r requirements.txt
python -m pytest tests/ -v          # run tests
python -m app.api                    # start dev server on :5000
```

Then open `http://localhost:5000`.

## Running via Docker

```bash
docker build -t dnd-encounter-tracker .
docker run -p 5000:5000 dnd-encounter-tracker
```

## API reference

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | health check |
| GET | `/encounters` | list all encounters |
| POST | `/encounters` | create an encounter (`{"name": "..."}`) |
| GET | `/encounters/{id}` | get encounter + turn order |
| DELETE | `/encounters/{id}` | delete an encounter |
| POST | `/encounters/{id}/combatants` | add combatant (`name`, `initiative`, `max_hp`, `is_pc`) |
| DELETE | `/encounters/{id}/combatants/{cid}` | remove combatant |
| POST | `/encounters/{id}/combatants/{cid}/damage` | apply damage (`{"amount": n}`) |
| POST | `/encounters/{id}/combatants/{cid}/heal` | apply healing (`{"amount": n}`) |
| POST | `/encounters/{id}/next-turn` | advance to next combatant's turn |

---

## Setup instructions (one-time)

Do these once before the pipelines will work.

### 1. Create the repo

In the `byui-itm350-a2s26` org, create a new repo named `{firstname}-{lastname}-final`
(e.g. `isaac-oliphant-final`). Push this project to it:

```bash
cd dnd-encounter-tracker
git init
git add .
git commit -m "Initial commit: app, tests, Dockerfile, CI/CD, Terraform"
git branch -M main
git remote add origin https://github.com/byui-itm350-a2s26/Isaac-Oliphant-final.git
git push -u origin main
```

### 2. Create a Docker Hub access token

1. Log into hub.docker.com -> Account Settings -> Security -> New Access Token
2. Name it something like `github-actions`, copy the token (you won't see it again)

### 3. Create an S3 bucket for Terraform state

Terraform needs somewhere to store its state file so GitHub Actions runs are
consistent across runs. Create this once, by hand, the only time you'll touch
the AWS Console/CLI directly (or ask your instructor if one is already
provisioned for the class):

```bash
aws s3api create-bucket --bucket iro-dnd-tracker-final --region us-east-1
aws s3api put-bucket-versioning --bucket iro-dnd-tracker-final \
  --versioning-configuration Status=Enabled
```

If you truly cannot log into AWS at all, ask your instructor whether the
class org already has a shared state bucket you should point at instead.

### 4. Create an IAM user for GitHub Actions (or reuse one from Week 11)

This user needs permissions to manage EC2, Security Groups, Elastic IPs, and
read/write the state bucket. If you already created one for the Week 11 S3
pipeline, you can reuse it and just attach `AmazonEC2FullAccess` (or a
tighter custom policy) alongside its existing S3 permissions. Grab its
Access Key ID and Secret Access Key.

### 5. Add GitHub Secrets

In the repo: **Settings -> Secrets and variables -> Actions -> New repository secret**

| Secret name | Value |
|---|---|
| `DOCKERHUB_USERNAME` | your Docker Hub username |
| `DOCKERHUB_TOKEN` | the access token from step 2 |
| `AWS_ACCESS_KEY_ID` | from step 4 |
| `AWS_SECRET_ACCESS_KEY` | from step 4 |
| `TF_STATE_BUCKET` | the bucket name from step 3 |

This is what makes "deploy without logging into AWS" work: GitHub Actions
authenticates using these secrets, so you never type AWS credentials into
the console yourself.

---

## Day-to-day workflow

1. Branch off `main`: `git checkout -b feature/my-change`
2. Make changes, commit, push -> this triggers **Build** (tests run on every
   branch; the Docker image only gets pushed once merged to `main`)
3. Open a PR into `main`, review, merge
4. Merge to `main` triggers **Release**: Terraform provisions/updates the
   EC2 instance and points it at the newest `:latest` image
5. Check the **Release** workflow's logs for the `terraform output app_url`
   line - that's your EC2 URL

To force a redeploy without a code change (e.g. after pushing a new image
tag manually), trigger **Release** manually from the Actions tab
(`workflow_dispatch`).

---

## Submission checklist

- [ ] EC2 URL - from `terraform output app_url` in the Release workflow logs
- [ ] Screenshot of the app running (open the EC2 URL in a browser, create
      an encounter, add a couple combatants, screenshot it)
- [ ] Codebase URL - `https://github.com/byui-itm350-a2s26/Isaac-Oliphant-final`
- [ ] Docker Hub URL - `https://hub.docker.com/r/isaacoliphant/dnd-encounter-tracker`

## Troubleshooting

- **Release workflow fails on `terraform init`**: double check the
  `TF_STATE_BUCKET` secret matches the bucket you created and that the IAM
  user has `s3:GetObject`/`s3:PutObject`/`s3:ListBucket` on it.
- **EC2 is up but the site doesn't load**: SSH in (`ssh ec2-user@<ip>`, if
  your `ssh_cidr` allows your IP) and run `docker ps` / `docker logs dnd-app`
  to see if the container is running and what it's logging. Also check
  `/var/log/cloud-init-output.log` for `user_data` script errors.
- **New pushes to `main` don't seem to redeploy**: `user_data_replace_on_change`
  only forces a re-run of `user_data` when the rendered script content
  changes, which happens when the image tag variable changes. If you're
  reusing `:latest` for every build, the EC2 instance still needs the
  release workflow to run `terraform apply` again to trigger the redeploy.
