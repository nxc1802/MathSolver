export type MessageRole = 'user' | 'assistant' | 'system';

export type MessageType = 
  | 'text' 
  | 'status' 
  | 'dsl' 
  | 'analysis' 
  | 'error'
  | 'coordinates'
  | 'quiz'
  | 'hint'
  | 'step_solution';

export interface ChatMessage {
  id: string;
  role: MessageRole;
  type: MessageType;
  content: string;
  timestamp: number;
  metadata?: {
    coordinates?: Record<string, [number, number]>;
    /** New in API v4.0 */
    semantic_analysis?: string;
    polygon_order?: string[];
    circles?: Array<{ center: string; radius: number }>;
    drawing_phases?: Array<{
      phase: number;
      label: string;
      points: string[];
      segments: string[][];
    }>;
    /** Primary key from API / DB (snake_case) */
    video_url?: string;
    /** @deprecated Prefer video_url */
    videoUrl?: string;
    job_id?: string;
    /** @deprecated Prefer job_id */
    jobId?: string;
    geometry_dsl?: string;
    image_url?: string;
  };
}

export interface ChatSession {
  id: string;
  user_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}
