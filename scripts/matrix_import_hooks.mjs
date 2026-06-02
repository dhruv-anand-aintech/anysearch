/**
 * Node loader hooks so worker/matrix.js can be imported for predeploy verification
 * (Wrangler bundles JSON/txt at deploy time; Node needs this shim).
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

export async function load(url, context, nextLoad) {
  if (url.endsWith(".json")) {
    const source = readFileSync(fileURLToPath(url), "utf8");
    return {
      format: "module",
      shortCircuit: true,
      source: `export default ${source}`,
    };
  }
  if (url.endsWith(".txt")) {
    const text = readFileSync(fileURLToPath(url), "utf8");
    return {
      format: "module",
      shortCircuit: true,
      source: `export default ${JSON.stringify(text)}`,
    };
  }
  return nextLoad(url, context);
}
