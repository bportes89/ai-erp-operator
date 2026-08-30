import { execSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

export default function globalSetup() {
  const python = process.env.PYTHON || "python";
  execSync(`${python} ${path.join(ROOT, "e2e", "fixtures", "generate.py")}`, { stdio: "inherit" });
}