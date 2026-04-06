'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { getApiBaseUrl } from '@/lib/runtime';
import { AgentSpeed, MatchSettings, ObstacleDensity } from '@/lib/types';

const agentSpeedOptions: Array<{ value: AgentSpeed; label: string; description: string }> = [
  { value: 'slow', label: 'Slow', description: 'The chaser moves every other tick.' },
  { value: 'normal', label: 'Normal', description: 'Balanced pursuit pressure.' },
  { value: 'fast', label: 'Fast', description: 'The chaser moves every tick.' }
];

const obstacleOptions: Array<{ value: ObstacleDensity; label: string; description: string }> = [
  { value: 'loose', label: 'Loose', description: 'Fewer blockers, more open lanes.' },
  { value: 'medium', label: 'Medium', description: 'Balanced obstacle spacing.' },
  { value: 'tight', label: 'Tight', description: 'Dense blockers, harder routing.' }
];

export default function HomePage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [settings, setSettings] = useState<MatchSettings>({
    agentSpeed: 'slow',
    obstacleDensity: 'medium',
    layoutTransform: false
  });

  const updateSettings = <K extends keyof MatchSettings,>(key: K, value: MatchSettings[K]) => {
    setSettings((current) => ({ ...current, [key]: value }));
  };

  const handleStart = async () => {
    try {
      setLoading(true);
      setError(null);
      const baseUrl = getApiBaseUrl();
      const response = await fetch(`${baseUrl}/matches`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ settings })
      });
      if (!response.ok) {
        throw new Error('Failed to create match');
      }
      const data: { matchId: string } = await response.json();
      router.push(`/battle?matchId=${data.matchId}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col justify-center px-6 py-16">
      <div className="rounded-[2rem] border border-slate-800 bg-slate-900/70 p-10 shadow-2xl">
        <div className="text-sm uppercase tracking-[0.3em] text-slate-400"> Beat the Agent!</div>
        <h1 className="mt-4 text-5xl font-bold tracking-tight">Make It Move</h1>
        <p className="mt-4 max-w-2xl text-lg text-slate-300">
          You are the runner. Finish every objective and survive the chaser for 120 seconds.
        </p>
        <div className="mt-8 grid gap-6 lg:grid-cols-2">
          <section className="rounded-3xl border border-slate-800 bg-slate-950/70 p-5">
            <div className="text-xs uppercase tracking-[0.25em] text-sky-300">Game Settings</div>
            <h2 className="mt-3 text-xl font-semibold">Agent Speed</h2>
            <div className="mt-4 grid gap-3">
              {agentSpeedOptions.map((option) => (
                <label
                  key={option.value}
                  className={`cursor-pointer rounded-2xl border p-4 transition ${
                    settings.agentSpeed === option.value
                      ? 'border-sky-400 bg-sky-500/10'
                      : 'border-slate-800 bg-slate-900/80 hover:border-slate-700'
                  }`}
                >
                  <input
                    type="radio"
                    name="agent-speed"
                    value={option.value}
                    checked={settings.agentSpeed === option.value}
                    onChange={() => updateSettings('agentSpeed', option.value)}
                    className="sr-only"
                  />
                  <div className="flex items-center justify-between gap-4">
                    <span className="text-lg font-semibold text-slate-100">{option.label}</span>
                    <span className="text-xs uppercase tracking-[0.2em] text-slate-400">{option.value}</span>
                  </div>
                  <p className="mt-2 text-sm text-slate-400">{option.description}</p>
                </label>
              ))}
            </div>
          </section>
          <section className="rounded-3xl border border-slate-800 bg-slate-950/70 p-5">
            <div className="text-xs uppercase tracking-[0.25em] text-amber-300">Board Density</div>
            <h2 className="mt-3 text-xl font-semibold">Obstacle Count</h2>
            <div className="mt-4 grid gap-3">
              {obstacleOptions.map((option) => (
                <label
                  key={option.value}
                  className={`cursor-pointer rounded-2xl border p-4 transition ${
                    settings.obstacleDensity === option.value
                      ? 'border-amber-400 bg-amber-400/10'
                      : 'border-slate-800 bg-slate-900/80 hover:border-slate-700'
                  }`}
                >
                  <input
                    type="radio"
                    name="obstacle-density"
                    value={option.value}
                    checked={settings.obstacleDensity === option.value}
                    onChange={() => updateSettings('obstacleDensity', option.value)}
                    className="sr-only"
                  />
                  <div className="flex items-center justify-between gap-4">
                    <span className="text-lg font-semibold text-slate-100">{option.label}</span>
                    <span className="text-xs uppercase tracking-[0.2em] text-slate-400">{option.value}</span>
                  </div>
                  <p className="mt-2 text-sm text-slate-400">{option.description}</p>
                </label>
              ))}
            </div>
          </section>
          <section className="rounded-3xl border border-slate-800 bg-slate-950/70 p-5 lg:col-span-2">
            <div className="text-xs uppercase tracking-[0.25em] text-fuchsia-300">Special Rule</div>
            <h2 className="mt-3 text-xl font-semibold">Layout Transform</h2>
            <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <div className="text-lg font-semibold text-slate-100">
                    {settings.layoutTransform ? 'Enabled' : 'Disabled'}
                  </div>
                  <p className="mt-2 max-w-2xl text-sm text-slate-400">
                    At 10s, 20s, 30s, 40s and 50s elapsed, the match pauses, marked walls flash, then the surviving
                    walls re-form in new positions.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => updateSettings('layoutTransform', !settings.layoutTransform)}
                  className={`rounded-full px-4 py-2 text-sm font-semibold ${
                    settings.layoutTransform ? 'bg-fuchsia-400 text-slate-950' : 'bg-slate-800 text-slate-100'
                  }`}
                >
                  {settings.layoutTransform ? 'On' : 'Off'}
                </button>
              </div>
            </div>
          </section>
        </div>
        <div className="mt-8 flex items-center gap-4">
          <button
            onClick={handleStart}
            disabled={loading}
            className="rounded-2xl bg-sky-500 px-6 py-3 text-lg font-semibold text-slate-950 hover:bg-sky-400 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading ? 'Creating match...' : 'Start Match'}
          </button>
          {error ? <span className="text-sm text-rose-300">{error}</span> : null}
        </div>
      </div>
    </main>
  );
}
