export default function ControlHint() {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4 text-sm text-slate-300">
      <div className="font-semibold text-slate-100">How to play</div>
      <ul className="mt-2 space-y-1">
        <li>Blue is the runner, red is the chaser.</li>
        <li>Touch every gold task marker before the timer ends.</li>
        <li>Wall bars sit between tiles and block movement and vision.</li>
        <li>Green swamps freeze whoever steps into them.</li>
        <li>Random events can freeze, boost, or reshape the chaser.</li>
        <li>Survive 120 seconds and finish all tasks to win.</li>
      </ul>
    </div>
  );
}
