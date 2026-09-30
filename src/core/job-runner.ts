import { randomUUID } from "node:crypto";
import { NoProviderAvailableError, ProviderRouter } from "./provider-router.js";
import { FileJobStore } from "./job-store.js";
import type { Checkpoint, Job } from "./types.js";

export class JobRunner {
  constructor(
    private readonly router: ProviderRouter,
    private readonly store: FileJobStore,
    private readonly retryMs = 15 * 60 * 1000,
  ) {}

  async create(goal: string): Promise<Job> {
    const now = new Date().toISOString();
    const job: Job = {
      id: randomUUID(),
      goal,
      status: "queued",
      step: 0,
      createdAt: now,
      updatedAt: now,
      metadata: {},
    };
    await this.store.saveJob(job);
    return job;
  }

  async runStep(job: Job): Promise<Job> {
    job.status = "running";
    job.updatedAt = new Date().toISOString();
    await this.store.saveJob(job);

    try {
      const result = await this.router.complete({
        messages: [{ role: "user", content: job.goal }],
      });
      job.step += 1;
      const checkpoint: Checkpoint = {
        id: randomUUID(),
        jobId: job.id,
        createdAt: new Date().toISOString(),
        step: job.step,
        summary: result.content,
        state: { provider: result.provider, model: result.model },
      };
      await this.store.saveCheckpoint(checkpoint);
      job.lastCheckpointId = checkpoint.id;
      job.status = "completed";
      delete job.nextRunAt;
    } catch (error) {
      if (error instanceof NoProviderAvailableError) {
        job.status = "waiting_for_quota";
        job.nextRunAt = new Date(Date.now() + this.retryMs).toISOString();
      } else {
        job.status = "failed";
        job.metadata.lastError = error instanceof Error ? error.message : String(error);
      }
    }

    job.updatedAt = new Date().toISOString();
    await this.store.saveJob(job);
    return job;
  }
}
