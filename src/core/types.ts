export type JobStatus =
  | "queued"
  | "running"
  | "waiting_for_quota"
  | "paused"
  | "completed"
  | "failed";

export interface Checkpoint {
  id: string;
  jobId: string;
  createdAt: string;
  step: number;
  summary: string;
  state: Record<string, unknown>;
}

export interface Job {
  id: string;
  goal: string;
  status: JobStatus;
  step: number;
  createdAt: string;
  updatedAt: string;
  nextRunAt?: string;
  lastCheckpointId?: string;
  metadata: Record<string, unknown>;
}

export interface ModelRequest {
  messages: Array<{ role: "system" | "user" | "assistant"; content: string }>;
  preferredModel?: string;
}

export interface ModelResponse {
  provider: string;
  model: string;
  content: string;
}

export interface Provider {
  readonly id: string;
  isAvailable(): Promise<boolean>;
  complete(request: ModelRequest): Promise<ModelResponse>;
}
