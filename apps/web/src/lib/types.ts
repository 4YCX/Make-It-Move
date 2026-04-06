export type PlayerAction = 'up' | 'down' | 'left' | 'right' | 'idle';

export interface EntityState {
  x: number;
  y: number;
  score: number;
}

export interface PointItem {
  id: string;
  x: number;
  y: number;
}

export interface WallSegment extends PointItem {
  orientation: 'horizontal' | 'vertical';
}

export interface TaskItem extends PointItem {
  completed: boolean;
}

export type AgentSpeed = 'slow' | 'normal' | 'fast';
export type ObstacleDensity = 'loose' | 'medium' | 'tight';

export interface MatchSettings {
  agentSpeed: AgentSpeed;
  obstacleDensity: ObstacleDensity;
  layoutTransform: boolean;
}

export interface MatchState {
  tick: number;
  remainingMs: number;
  status: 'pending' | 'running' | 'finished';
  gridSize: number;
  winner?: 'human' | 'agent' | 'draw' | null;
  settings: MatchSettings;
  human: EntityState;
  agent: EntityState;
  walls: WallSegment[];
  swamps: PointItem[];
  tasks: TaskItem[];
  latestEvent: string | null;
  humanStunTicks: number;
  agentStunTicks: number;
  agentVisionRadius: number;
  activeEventType?: 'freeze' | 'boost' | 'transform' | 'decay' | 'task' | null;
  eventDisplayTicks: number;
  layoutTransformTicks: number;
  highlightedWalls: string[];
}

export type WsMessage =
  | { type: 'MATCH_STATE'; payload: MatchState }
  | { type: 'MATCH_RESULT'; payload: { winner: 'human' | 'agent' | 'draw' } }
  | { type: 'ERROR'; payload: { message: string } }
  | { type: 'PONG'; payload: Record<string, never> };
