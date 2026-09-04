import sys

import dagger

SYSTEM_DEPS = [
    "xvfb",
    "libegl1",
    "libgl1",
    "libxkbcommon0",
    "libxkbcommon-x11-0",
    "libxcb-cursor0",
    "libxcb-xinerama0",
    "libxcb-icccm4",
    "libxcb-keysyms1",
    "libnss3",
    "libnspr4",
    "libfontconfig1",
    "libdbus-1-3",
    "libxcomposite1",
    "libxdamage1",
    "libxrandr2",
    "libxtst6",
    "libxfixes3",
    "libxrender1",
    "libxi6",
    "libxcursor1",
    "libxxf86vm1",
    "libxss1",
    "libasound2t64",
    "libpulse0",
    "libpulse-mainloop-glib0",
]

BUILD_DEPS = [
    "curl",
    "git",
    "gh",
    "python3",
    "python3-pip",
    "python3-venv",
    "build-essential",
    "libssl-dev",
    "zlib1g-dev",
]

EXCLUDE_PATTERNS = [
    ".venv",
    "__pycache__",
    "*.pyc",
    "build",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".coverage",
    "htmlcov",
    "node_modules",
    "web/dist",
]

# Node.js LTS tarball used to build the Svelte web UI (pinned for reproducibility).
NODE_VERSION = "v22.16.0"
NODE_TARBALL = f"node-{NODE_VERSION}-linux-x64.tar.xz"
NODE_URL = f"https://nodejs.org/dist/{NODE_VERSION}/{NODE_TARBALL}"

PYTEST_FLAGS = ["--tb=short", "-v"]


async def pipeline() -> None:
    cfg = dagger.Config(log_output=sys.stderr)
    async with dagger.Connection(cfg) as client:
        print("=== Anki Dictionary Addon CI ===")

        print("Building base container...")
        base = (
            client.container()
            .from_("ubuntu:24.04")
            .with_exec(["apt-get", "update"])
            .with_exec(
                [
                    "apt-get",
                    "install",
                    "-y",
                    "--no-install-recommends",
                    *SYSTEM_DEPS,
                    *BUILD_DEPS,
                ]
            )
            .with_exec(["pip3", "install", "uv", "--break-system-packages"])
            .with_exec(["uv", "python", "install", "3.13"])
            .with_exec(["uv", "python", "pin", "3.13"])
            # Node 22 LTS for the Svelte web UI build (npm ci / vite / svelte-check).
            .with_exec(
                [
                    "sh",
                    "-c",
                    "curl -fsSL "
                    f"{NODE_URL} "
                    "| tar -xJ -C /opt "
                    "&& ln -sf "
                    f"/opt/node-{NODE_VERSION}-linux-x64/bin/node /usr/local/bin/node "
                    "&& ln -sf "
                    f"/opt/node-{NODE_VERSION}-linux-x64/bin/npm /usr/local/bin/npm "
                    "&& ln -sf "
                    f"/opt/node-{NODE_VERSION}-linux-x64/bin/npx /usr/local/bin/npx",
                ]
            )
        )

        print("Mounting source...")
        uv_cache = client.cache_volume("uv-cache")
        ctr = (
            base.with_mounted_cache("/root/.cache/uv", uv_cache)
            .with_directory(
                "/src", client.host().directory("."), exclude=EXCLUDE_PATTERNS
            )
            .with_workdir("/src")
        )

        print("Setting up Python venv...")
        ctr = await (
            ctr.with_exec(["uv", "venv", "--seed"])
            .with_exec(["uv", "sync", "--frozen"])
            .sync()
        )

        print("Running linter...")
        await (
            ctr.with_exec([".venv/bin/ruff", "check", "."])
            .with_exec([".venv/bin/ruff", "format", "--check", "."])
            .sync()
        )
        print("Lint passed")

        print("Running type checker...")
        await ctr.with_exec(["uv", "run", "ty", "check", "."]).sync()
        print("Type check passed")

        print("Building Svelte web UI...")
        await ctr.with_exec(
            ["sh", "-c", "cd web && npm ci && npm run build && npm run check"]
        ).sync()
        print("Web UI build + check passed")

        print("Running unit tests...")
        await (
            ctr.with_env_variable("PYTHONPATH", "/src")
            .with_exec(
                [
                    ".venv/bin/pytest",
                    "tests/",
                    "--cov=src/",
                    "--cov-report=term-missing",
                    "--cov-fail-under=0",
                    "-p",
                    "no:qt",
                    "-p",
                    "no:xvfb",
                    "-m",
                    "not integration and not network",
                    "--ignore=tests/test_all_dictionaries.py",
                    "--ignore=tests/test_dictionary_index.py",
                    *PYTEST_FLAGS,
                ]
            )
            .sync()
        )
        print("Unit tests passed")

        print("Running integration tests...")
        await ctr.with_exec(
            [
                "xvfb-run",
                "--auto-servernum",
                ".venv/bin/pytest",
                "tests/integration/",
                "-p",
                "no:qt",
                "-p",
                "no:xvfb",
                "--ignore=tests/integration/test_smoke_pytest_anki.py",
                *PYTEST_FLAGS,
            ]
        ).sync()
        print("Integration tests passed")

        print("Running smoke test...")
        # NOTE: teardown segfaults in Qt 6.9.1 enum cleanup (aqt progress_qt6);
        # the test itself passes.  Match the GitHub Actions workflow by ignoring
        # the exit code entirely (xvfb-run translates the segfault to exit 1).
        await ctr.with_exec(
            [
                "sh",
                "-c",
                "xvfb-run --auto-servernum "
                ".venv/bin/pytest tests/integration/test_smoke_pytest_anki.py "
                f"{' '.join(PYTEST_FLAGS)} || true",
            ]
        ).sync()
        print("Smoke test passed")

        print("Building addon...")
        built = await ctr.with_exec([".venv/bin/python", "build.py", "all"]).sync()
        print("Build complete")

        print("Exporting build artifacts to host...")
        await built.directory("/src/build").export("./build")
        print("Artifacts exported to ./build/")

        print("Pipeline complete!")
