import { loadProvidersFromEnv } from "./config/providers.js";
import { FileJobStore } from "./core/job-store.js";
import { JobRunner } from "./core/job-runner.js";
import { ProviderRouter } from "./core/provider-router.js";

const providers = loadProvidersFromEnv();
const router = new ProviderRouter(providers);
const store = new FileJobStore();
const runner = new JobRunner(router, store);

const goal = process.argv.slice(2).join(" ").trim();
if (!goal) {
  console.log(`CT-AI ready with ${providers.length} configured provider(s). Pass a goal to create a persistent job.`);
  process.exit(0);
}
const job = await runner.create(goal);
console.log(JSON.stringify(await runner.runStep(job), null, 2));
