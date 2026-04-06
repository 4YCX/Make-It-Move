'use client';

import { MatchState } from '@/lib/types';

interface ArenaProps {
  state: MatchState;
}

const CELL_SIZE = 22;
const CELL_GAP = 6;
const WALL_THICKNESS = 4;
const HIGHLIGHT_THICKNESS = 18;

export default function Arena({ state }: ArenaProps) {
  const { gridSize, human, agent } = state;
  const walls = state.walls ?? [];
  const swamps = state.swamps ?? [];
  const tasks = state.tasks ?? [];
  const highlightedWalls = new Set(state.highlightedWalls ?? []);
  const decayPreviewActive = state.activeEventType === 'decay' && state.eventDisplayTicks > 0;
  const cells = [];
  const boardSize = gridSize * CELL_SIZE + (gridSize - 1) * CELL_GAP;

  for (let y = 0; y < gridSize; y += 1) {
    for (let x = 0; x < gridSize; x += 1) {
      const swamp = swamps.find((item) => item.x === x && item.y === y);
      const task = tasks.find((item) => item.x === x && item.y === y && !item.completed);
      const isHuman = human.x === x && human.y === y;
      const isAgent = agent.x === x && agent.y === y;

      let toneClasses = 'border-slate-800 bg-slate-900';
      let label = '';

      if (swamp) {
        toneClasses = 'border-emerald-800 bg-emerald-950';
        label = 'swamp';
      }
      if (task) {
        toneClasses = 'border-amber-300 bg-amber-400';
        label = 'task';
      }
      if (isHuman) {
        toneClasses = 'border-sky-300 bg-sky-500';
        label = 'runner';
      }
      if (isAgent) {
        toneClasses = 'border-rose-300 bg-rose-500';
        label = 'chaser';
      }
      if (isHuman && isAgent) {
        toneClasses = 'border-violet-200 bg-violet-500';
        label = 'caught';
      }

      cells.push(
        <div
          key={`${x}-${y}`}
          className={`h-full w-full rounded-[4px] border ${toneClasses}`}
          title={`${x},${y} ${label}`.trim()}
        />
      );
    }
  }

  const wallSegments = walls.map((wall) => {
    const offset = wall.x * (CELL_SIZE + CELL_GAP);
    const lane = wall.y * (CELL_SIZE + CELL_GAP);
    const highlighted = highlightedWalls.has(wall.id);
    const thickness = highlighted ? HIGHLIGHT_THICKNESS : WALL_THICKNESS;

    if (wall.orientation === 'vertical') {
      return (
        <div
          key={wall.id}
          className={`absolute rounded-full ${
            highlighted
              ? 'wall-warning bg-fuchsia-300 shadow-[0_0_32px_rgba(244,114,182,0.95)]'
              : decayPreviewActive
                ? 'bg-slate-500/20 shadow-none'
                : 'bg-slate-300/90 shadow-[0_0_12px_rgba(226,232,240,0.2)]'
          }`}
          style={{
            height: `${CELL_SIZE}px`,
            left: `${offset + CELL_SIZE + (CELL_GAP - thickness) / 2}px`,
            top: `${lane}px`,
            width: `${thickness}px`
          }}
        />
      );
    }

    return (
      <div
        key={wall.id}
        className={`absolute rounded-full ${
          highlighted
            ? 'wall-warning bg-fuchsia-300 shadow-[0_0_32px_rgba(244,114,182,0.95)]'
            : decayPreviewActive
              ? 'bg-slate-500/20 shadow-none'
              : 'bg-slate-300/90 shadow-[0_0_12px_rgba(226,232,240,0.2)]'
        }`}
        style={{
          height: `${thickness}px`,
          left: `${offset}px`,
          top: `${lane + CELL_SIZE + (CELL_GAP - thickness) / 2}px`,
          width: `${CELL_SIZE}px`
        }}
      />
    );
  });

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-950/70 p-4 shadow-2xl">
      <div
        className="relative mx-auto"
        style={{ height: `${boardSize}px`, width: `${boardSize}px` }}
      >
        <div
          className="grid"
          style={{
            gap: `${CELL_GAP}px`,
            gridAutoRows: `${CELL_SIZE}px`,
            gridTemplateColumns: `repeat(${gridSize}, ${CELL_SIZE}px)`
          }}
        >
          {cells}
        </div>
        <div className="pointer-events-none absolute inset-0">{wallSegments}</div>
      </div>
    </div>
  );
}
