import { z } from "zod";

export const SolverPhaseSchema = z.enum(["idle", "uploading", "ocr", "parsing", "solving", "rendering", "success", "error", "rendering_queued", "processing"]);
export type SolverPhase = z.infer<typeof SolverPhaseSchema>;

export const DrawingPhaseSchema = z.object({
  phase: z.number(),
  label: z.string(),
  points: z.array(z.string()),
  segments: z.array(z.array(z.string())),
});

export const SolutionSchema = z.object({
  answer: z.string(),
  steps: z.array(z.string()).optional(),
  symbolic_math: z.record(z.string(), z.string()).optional(),
});

export const GeometryMetadataSchema = z.object({
  coordinates: z.record(z.string(), z.union([z.tuple([z.number(), z.number()]), z.tuple([z.number(), z.number(), z.number()])])).optional(),
  semantic_analysis: z.string().optional(),
  polygon_order: z.array(z.string()).optional(),
  circles: z.array(z.object({ center: z.string(), radius: z.number() })).optional(),
  drawing_phases: z.array(DrawingPhaseSchema).optional(),
  lines: z.array(z.tuple([z.string(), z.string()])).optional(),
  rays: z.array(z.tuple([z.string(), z.string()])).optional(),
  solution: SolutionSchema.optional(),
  is_3d: z.boolean().optional(),
  video_url: z.string().optional(),
  videoUrl: z.string().optional(),
  job_id: z.string().optional(),
  jobId: z.string().optional(),
  geometry_dsl: z.string().optional(),
  image_url: z.string().optional(),
});
export type GeometryMetadata = z.infer<typeof GeometryMetadataSchema>;

export const JobStateSchema = z.object({
  phase: SolverPhaseSchema,
  progress: z.number(),
  message: z.string(),
  result: GeometryMetadataSchema.optional(),
  error: z.string().optional(),
});
export type JobState = z.infer<typeof JobStateSchema>;
