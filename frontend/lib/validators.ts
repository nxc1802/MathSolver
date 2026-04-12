import { z } from "zod";

export const CoordinatesSchema = z.record(
  z.string(),
  z.union([z.tuple([z.number(), z.number()]), z.tuple([z.number(), z.number(), z.number()])])
);

export const DrawingPhaseSchema = z.object({
  phase: z.number(),
  label: z.string(),
  points: z.array(z.string()),
  segments: z.array(z.array(z.string())),
});

export const SolutionSchema = z.object({
  answer: z.string(),
  steps: z.array(z.string()),
  symbolic_math: z.record(z.string(), z.string()).optional(),
});

export const JobResultSchema = z.object({
  job_id: z.string().optional(),
  semantic_analysis: z.string().optional(),
  geometry_dsl: z.string().optional(),
  coordinates: CoordinatesSchema.optional(),
  polygon_order: z.array(z.string()).optional(),
  circles: z.array(z.object({ center: z.string(), radius: z.number() })).optional(),
  lines: z.array(z.tuple([z.string(), z.string()])).optional(),
  rays: z.array(z.tuple([z.string(), z.string()])).optional(),
  drawing_phases: z.array(DrawingPhaseSchema).optional(),
  solution: SolutionSchema.optional(),
  is_3d: z.boolean().optional(),
  video_url: z.string().optional(),
}).catchall(z.any()); // Accept other fields if they exist

export type JobResult = z.infer<typeof JobResultSchema>;

export function validateJobResult(data: any): JobResult {
  const result = JobResultSchema.safeParse(data);
  if (result.success) {
    return result.data;
  }
  console.error("JobResult validation failed:", result.error);
  // Return the original data loosely shaped if validation fails, 
  // so we don't break the app entirely, just warn.
  return data as JobResult;
}
