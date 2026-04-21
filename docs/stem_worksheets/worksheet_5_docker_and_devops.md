# Worksheet 5: Docker and DevOps

**Subject:** Computer Science / Software Engineering  
**Grade level:** 10–12  
**Estimated time:** 55 minutes  
**Prerequisite knowledge:** Basic command line, some Python

---

## Learning Objectives

1. Explain what Docker is and why containers are useful.
2. Distinguish between a Docker **image** and a Docker **container**.
3. Read a `Dockerfile` and explain what each instruction does.
4. Run the hexapod stack using `docker compose`.
5. Explain what a CI/CD pipeline is and read the GitHub Actions workflow.

---

## Background: What Is Docker?

### The Dependency Problem

Imagine you write a Python program that works perfectly on your laptop.
Your friend tries to run it — but gets an error because they have a different
version of Python, or a missing library, or a different operating system.

"But it works on *my* machine!" is a joke that every software developer knows.

**Docker** solves this by packaging your program *together with everything it needs*:
the correct Python version, all libraries, system dependencies — into a single
portable unit called a **container**.

### Containers vs. Virtual Machines

```
Virtual Machine                    Container
┌──────────────────────┐           ┌──────────────────────┐
│   App A   │   App B  │           │   App A   │   App B  │
├───────────┼──────────┤           ├───────────┼──────────┤
│  Guest OS │  Guest OS│           │  Libs     │  Libs    │
├───────────┴──────────┤           ├──────────────────────┤
│       Hypervisor     │           │  Container Runtime   │
├──────────────────────┤           │  (Docker Engine)     │
│    Host OS + CPU     │           ├──────────────────────┤
└──────────────────────┘           │    Host OS + CPU     │
                                   └──────────────────────┘

VMs: heavy, full OS per app         Containers: lightweight, share host OS kernel
```

Containers are typically 10–100× faster to start than virtual machines.

---

## Reading a Dockerfile: Dockerfile.core

Open `docker/Dockerfile.core` in a text editor.  Answer the questions below.

```dockerfile
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev && rm -rf /var/lib/apt/lists/*

COPY software/requirements.txt .

RUN pip install --no-cache-dir --prefix=/install fastapi uvicorn ...

FROM python:3.11-slim AS runtime

COPY --from=builder /install /usr/local

WORKDIR /app
COPY software/hexapod_core/ ./hexapod_core/

EXPOSE 8000

CMD ["uvicorn", "hexapod_core.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Exercise 5.1:** Match each Dockerfile instruction to its meaning.

| Instruction | Meaning |
|---|---|
| `FROM python:3.11-slim` | A. Run a shell command during image build |
| `WORKDIR /build` | B. Set the base image to start from |
| `RUN apt-get install …` | C. Set the working directory |
| `COPY requirements.txt .` | D. Copy file from host into image |
| `EXPOSE 8000` | E. The default command when container starts |
| `CMD [...]` | F. Document which network port the app uses |

**Answers:** FROM=___, WORKDIR=___, RUN=___, COPY=___, EXPOSE=___, CMD=___

---

## Exercise 5.2: Multi-Stage Builds

Notice the Dockerfile has **two** `FROM` lines:

```dockerfile
FROM python:3.11-slim AS builder   ← Stage 1
...
FROM python:3.11-slim AS runtime   ← Stage 2
```

**Question 1:** Why would you want two stages?  What is copied from stage 1 to stage 2?

_________________________________________________________________________

**Question 2:** `COPY --from=builder /install /usr/local` — what does `--from=builder` mean?

_________________________________________________________________________

**Question 3:** The `builder` stage installs `gcc` (a compiler).  
Why is `gcc` *not* needed in the `runtime` stage?

_________________________________________________________________________

---

## Running Docker Compose

Docker Compose lets you start multiple containers together.

```bash
# From the repo root:

# Start the core API and UI
docker compose up -d hexapod-core hexapod-ui

# View running containers
docker compose ps

# Read logs (press Ctrl+C to stop)
docker compose logs -f hexapod-core

# Stop everything
docker compose down
```

**Exercise 5.3:** Read `docker/docker-compose.yml` and answer:

1. How many services are defined?  ___

2. Which service depends on `hexapod-core` being healthy first?  ___

3. What does `privileged: true` allow?  Why is it needed for this robot?

   _________________________________________________________________________

4. What does `profiles: [vision]` mean for the `hexapod-vision` service?
   How do you start it?

   _________________________________________________________________________

5. What is the purpose of the `networks` section?  
   What would happen if two services were on different networks?

   _________________________________________________________________________

---

## Environment Variables

Environment variables are a safe way to configure software without hardcoding values.

```yaml
environment:
  - I2C_BUS=1
  - PCA9685_ADDRESS=0x40
  - LOG_LEVEL=INFO
```

**Exercise 5.4:** Add a new environment variable `MAX_SPEED_MS` (maximum speed in m/s)
to the `hexapod-core` service in `docker-compose.yml`.

Write the line you would add:

```
_________________________
```

Now read it in Python:

```python
import os
MAX_SPEED = float(os.getenv("MAX_SPEED_MS", "0.15"))
```

---

## What Is CI/CD?

**CI** = Continuous Integration — automatically test code whenever anyone pushes a change.  
**CD** = Continuous Deployment — automatically deploy working code to production.

### GitHub Actions

GitHub Actions runs automated workflows defined in YAML files in `.github/workflows/`.

Open `.github/workflows/ci.yml`.  The workflow has **three jobs**:

1. **lint** — checks code style (flake8 + black).
2. **test** — runs `pytest` to verify the code works.
3. **docker-build** — builds all three Docker images.

```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
```

**Exercise 5.5:** Answer these questions about `ci.yml`:

1. When does the CI pipeline run?

   _________________________________________________________________________

2. The `test` job installs packages with `pip install …` but *excludes* `RPi.GPIO`.
   Why can RPi.GPIO not be installed on the GitHub Actions runner?

   _________________________________________________________________________

3. The `docker-build` job has `needs: [lint, test]`.  What does this mean?

   _________________________________________________________________________

---

## Exercise 5.6: Add a New Test

Write a new pytest test and add it to `software/tests/test_ik_solver.py`.

**Task:** Test that the IK solver works for a foot position directly to the left:
`x = 0.12, y = 0.10, z = -0.08`

```python
def test_solve_left_position():
    ik = LegIK()
    coxa, femur, tibia = ik.solve(x=0.12, y=0.10, z=-0.08)
    # Coxa should be positive (left = positive y → positive yaw)
    assert coxa > 0, f"Expected positive coxa for left target, got {coxa}"
    # Tibia should be between 0 and 180
    assert 0 <= tibia <= 180
```

**Steps:**
1. Add the test to the file.
2. Run: `pytest software/tests/test_ik_solver.py::test_solve_left_position -v`
3. Did it pass?  ___
4. Commit the change: `git add . && git commit -m "test: add left-position IK test"`
5. Push to GitHub — does the CI pipeline run?  ___

---

## Vocabulary

| Term | Definition |
|---|---|
| Docker | Software platform for building and running containers |
| Container | Isolated, portable package containing an app and all dependencies |
| Image | Read-only template used to create containers |
| Dockerfile | Script of instructions to build a Docker image |
| Docker Compose | Tool for defining and running multi-container Docker applications |
| CI | Continuous Integration — auto-test on every code change |
| CD | Continuous Deployment — auto-deploy tested code |
| GitHub Actions | CI/CD platform built into GitHub |
| Environment variable | Named value passed to a process from outside the code |
| Multi-stage build | Dockerfile technique using multiple `FROM` to reduce image size |
| `EXPOSE` | Documents which port the containerised app listens on |
| Health check | Automated test to verify a container is running correctly |

---

## Challenge: Shrink the Docker Image

The `hexapod-core` image includes `scipy` (≈80 MB installed).

1. Run `docker images hexapod-core:ci` to see the image size.
2. Find which packages are the largest: `docker run --rm hexapod-core:ci pip list --format=columns | sort -k3 -n`
3. Can `scipy` be removed if only `numpy` is needed for the IK solver?  What would break?
4. Rebuild without `scipy` and compare image sizes.

---

*Congratulations! You have completed all five STEM worksheets.*  
*You now understand how a real hexapod robot works from hardware to cloud!*
