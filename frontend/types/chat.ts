import type { GeometryMetadata } from './geometry';

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
  metadata?: GeometryMetadata;
}

export interface ChatSession {
  id: string;
  user_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}
