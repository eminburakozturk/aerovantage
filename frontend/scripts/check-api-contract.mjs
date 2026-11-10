import fs from "node:fs";
import path from "node:path";
import process from "node:process";

const repoRoot = process.cwd();
const snapshotPath = path.join(repoRoot, "scripts", "api-contract.snapshot.json");
const apiEntrypointPath = path.join(repoRoot, "src", "lib", "api.ts");
const apiIndexPath = path.join(repoRoot, "src", "lib", "api", "index.ts");

function fail(message) {
  process.stderr.write(`${message}\n`);
  process.exit(1);
}

function readJson(filePath) {
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch (error) {
    fail(`API contract snapshot okunamadi: ${filePath}\n${error}`);
  }
}

function parseExportTargets(source) {
  const matches = source.matchAll(/export\s+\*\s+from\s+["'](.+?)["'];?/g);
  return [...matches].map((match) => match[1]);
}

const snapshot = readJson(snapshotPath);

const apiEntrypointSource = fs.readFileSync(apiEntrypointPath, "utf8");
const apiIndexSource = fs.readFileSync(apiIndexPath, "utf8");

const entrypointTargets = parseExportTargets(apiEntrypointSource);
const indexTargets = parseExportTargets(apiIndexSource);

if (entrypointTargets.length !== 1 || entrypointTargets[0] !== snapshot.entrypointTarget) {
  fail(
    `api.ts export contract bozuldu. Beklenen: ${snapshot.entrypointTarget}, bulunan: ${entrypointTargets.join(", ")}`,
  );
}

if (JSON.stringify(indexTargets) !== JSON.stringify(snapshot.indexExportTargets)) {
  fail(
    `api/index.ts export contract bozuldu.\nBeklenen: ${snapshot.indexExportTargets.join(", ")}\nBulunan: ${indexTargets.join(", ")}`,
  );
}

process.stdout.write("API contract check OK\n");

