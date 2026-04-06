'use client';

import { MatchState } from '@/lib/types';

interface ScorePanelProps {
  state: MatchState;
  winner?: 'human' | 'agent' | 'draw' | null;
}

export default function ScorePanel({ state, winner }: ScorePanelProps) {
  const settings = state.settings ?? { agentSpeed: 'slow', obstacleDensity: 'medium', layoutTransform: false };
  const completedTasks = state.tasks?.filter((task) => task.completed).length ?? state.human.score;

  return (
    <div className="grid gap-4 md:grid-cols-3">
      <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
        <div className="text-xs uppercase tracking-[0.2em] text-sky-300">Runner</div>
        <div className="mt-2 text-3xl font-bold">{completedTasks}/{Math.max(state.tasks?.length ?? 0, 1)}</div>
        <div className="mt-2 text-sm text-slate-400">Finish every objective, then survive.</div>
      </div>
      <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 text-center">
        <div className="text-xs uppercase tracking-[0.2em] text-slate-400">Timer</div>
        <div className="mt-2 text-3xl font-bold">{Math.ceil(state.remainingMs / 1000)}s</div>
        <div className="mt-2 text-sm text-slate-400">
          Runner stun: {state.humanStunTicks} | Chaser stun: {state.agentStunTicks}
        </div>
      </div>
      <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 text-right">
        <div className="text-xs uppercase tracking-[0.2em] text-rose-300">Chaser</div>
        <div className="mt-2 text-3xl font-bold">{state.agent.score ? 'Caught' : 'Hunting'}</div>
        <div className="mt-2 text-sm text-slate-400">Policy: shortest path pursuit</div>
        <div className="mt-1 text-sm text-slate-500">Speed: {settings.agentSpeed}</div>
        <div className="mt-1 text-sm text-slate-500">Vision: {state.agentVisionRadius} cells</div>
      </div>
      <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 md:col-span-3">
        <div className="text-xs uppercase tracking-[0.2em] text-amber-300">Briefing</div>
        <div className="mt-3 flex flex-wrap gap-3 text-sm text-slate-300">
          <span className="rounded-full border border-slate-700 px-3 py-1">Agent speed: {settings.agentSpeed}</span>
          <span className="rounded-full border border-slate-700 px-3 py-1">Obstacles: {settings.obstacleDensity}</span>
          <span className="rounded-full border border-slate-700 px-3 py-1">
            Layout transform: {settings.layoutTransform ? 'enabled' : 'disabled'}
          </span>
          <span className="rounded-full border border-slate-700 px-3 py-1">Tasks: {state.tasks?.length ?? 0}</span>
        </div>
        <div className="mt-4 rounded-2xl border border-slate-700 bg-slate-950/60 px-4 py-3 text-sm text-slate-300 transition">
          <div className="text-xs uppercase tracking-[0.2em] opacity-70">Live Event</div>
          <div className="mt-1 text-base font-medium">{state.latestEvent ?? 'No live event.'}</div>
        </div>
      </div>
      {winner ? (
        <div className="rounded-2xl border border-emerald-800 bg-emerald-950/40 p-4 md:col-span-3">
          <div className="text-xs uppercase tracking-[0.2em] text-emerald-300">Result</div>
          <div className="mt-2 text-2xl font-semibold">
            {winner === 'draw' ? 'Draw' : winner === 'human' ? 'Runner escapes' : 'Chaser wins'}
          </div>
        </div>
      ) : null}
    </div>
  );
}
