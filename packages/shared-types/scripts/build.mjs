import { execSync } from "node:child_process";
import { existsSync, copyFileSync } from "node:fs";

const source = "../../apps/api/openapi.json";
const target = "./index.d.ts";

if (!existsSync(source)) {
  const fallback = "./index.fallback.d.ts";
  copyFileSync(fallback, target);
  process.stdout.write("openapi.json missing; copied fallback types\n");
  process.exit(0);
}

try {
  execSync(`openapi-typescript ${source} -o ${target}`, { stdio: "inherit" });
} catch {
  const fallback = "./index.fallback.d.ts";
  copyFileSync(fallback, target);
  process.stdout.write("openapi-typescript unavailable; copied fallback types\n");
}
