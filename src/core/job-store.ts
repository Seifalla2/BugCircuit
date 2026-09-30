import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import type { Checkpoint, Job } from "./types.js";

interface StateFile {
  jobs: Job[];
  checkpoints: Checkpoint[];
}

export class FileJobStore {
  private readonly path: string;

  constructor(dataDir = process.env.CT_AI_DATA_DIR ?? "./data") {
    this.path = join(dataDir, "state.json");
  }

  private async read(): Promise<StateFile> {
    try {
      return JSON.parse(await readFile(this.path, "utf8")) as StateFile;
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code === "ENOENT") {
        return { jobs: [], checkpoints: [] };
      }
      throw error;
    }
  }

  private async write(state: StateFile): Promise<void> {
    await mkdir(dirname(this.path), { recursive: true });
    await writeFile(this.path, JSON.stringify(state, null, 2));
  }

  async saveJob(job: Job): Promise<void> {
    const state = await this.read();
    const index = state.jobs.findIndex((item) => item.id === job.id);
    if (index >= 0) state.jobs[index] = job;
    else state.jobs.push(job);
    await this.write(state);
  }

  async saveCheckpoint(checkpoint: Checkpoint): Promise<void> {
    const state = await this.read();
    state.checkpoints.push(checkpoint);
    await this.write(state);
  }
}
