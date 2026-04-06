'use client';

import { PlayerAction } from '@/lib/types';

interface TouchControlsProps {
  disabled?: boolean;
  onAction: (action: PlayerAction) => void;
}

const controls: Array<{ action: PlayerAction; label: string; className: string }> = [
  { action: 'up', label: 'Up', className: 'col-start-2 row-start-1' },
  { action: 'left', label: 'Left', className: 'col-start-1 row-start-2' },
  { action: 'down', label: 'Down', className: 'col-start-2 row-start-2' },
  { action: 'right', label: 'Right', className: 'col-start-3 row-start-2' }
];

export default function TouchControls({ disabled, onAction }: TouchControlsProps) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
      <div className="text-sm font-semibold text-slate-100">Controls</div>
      <div className="mt-3 grid grid-cols-3 gap-2">
        {controls.map((control) => (
          <button
            key={control.action}
            type="button"
            disabled={disabled}
            onClick={() => onAction(control.action)}
            className={`rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm font-semibold text-slate-100 hover:border-sky-400 hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40 ${control.className}`}
          >
            {control.label}
          </button>
        ))}
      </div>
    </div>
  );
}
