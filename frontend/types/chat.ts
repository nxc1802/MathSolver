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
    videoUrl?: string;
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
