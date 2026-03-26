export type MessageRole = 'user' | 'assistant' | 'system';

export type MessageType = 
  | 'text' 
  | 'status' 
  | 'dsl' 
  | 'analysis' 
  | 'error'
  | 'coordinates'
  // Future extensibility for tutoring app
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
  };
}
