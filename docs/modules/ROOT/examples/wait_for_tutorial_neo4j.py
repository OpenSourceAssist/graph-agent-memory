"""Wait at most three minutes for the named tutorial Docker database."""

import argparse
import subprocess
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("container")
    args = parser.parse_args()
    deadline = time.monotonic() + 180
    last = "No response"
    while time.monotonic() < deadline:
        try:
            result = subprocess.run(
                [
                    "docker",
                    "exec",
                    args.container,
                    "cypher-shell",
                    "-u",
                    "neo4j",
                    "-p",
                    "docs-local-password",
                    "RETURN 1 AS ready",
                ],
                capture_output=True,
                text=True,
                timeout=min(10, max(1, deadline - time.monotonic())),
            )
        except subprocess.TimeoutExpired:
            last = "Readiness query timed out"
        else:
            if result.returncode == 0:
                print("Verified: Neo4j answered the readiness query")
                return
            last = result.stderr.strip()
        time.sleep(min(2, max(0, deadline - time.monotonic())))
    raise SystemExit(f"Neo4j was not ready within 180 seconds: {last}")


if __name__ == "__main__":
    main()
