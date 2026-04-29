import { spawnSync } from "node:child_process";

const pythonArgs = process.argv.slice(2);

if (pythonArgs.length === 0) {
  console.error("Usage: node scripts/run_python.mjs <script.py|-m module> [args...]");
  process.exit(2);
}

const candidates = [
  ...(process.env.PYTHON ? [[process.env.PYTHON]] : []),
  ["python3"],
  ["python"],
  ["py", "-3"]
];

for (const candidate of candidates) {
  const check = spawnSync(candidate[0], [...candidate.slice(1), "--version"], {
    encoding: "utf8",
    shell: false
  });

  if (check.status !== 0) {
    continue;
  }

  const result = spawnSync(candidate[0], [...candidate.slice(1), ...pythonArgs], {
    stdio: "inherit",
    shell: false
  });

  if (result.status === null && result.error) {
    console.error(result.error.message);
    process.exit(1);
  }

  process.exit(result.status ?? 1);
}

console.error("Could not find Python. Install Python 3 or set the PYTHON environment variable.");
process.exit(1);
