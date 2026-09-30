import { FileJobStore } from "./core/job-store.js";
import { JobRunner } from "./core/job-runner.js";
import { ProviderRouter } from "./core/provider-router.js";

const router = new ProviderRouter([]);
const store = new FileJobStore();
const runner = new JobRunner(router, store);

const goal = process.argv.slice(2).join(" ").trim();
if (!goal) {
  console.log("CT-AI foundation ready. Pass a goal to create a persistent job.");
  process.exit(0);
}

const job = await runner.create(goal);
const result = await runner.runStep(job);
console.log(JSON.stringify(result, null, 2));
