'use client';

import { Suspense, useEffect, useMemo, useRef, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Arena from '@/components/Arena';
import ScorePanel from '@/components/ScorePanel';
import ControlHint from '@/components/ControlHint';
import TouchControls from '@/components/TouchControls';
import { getWsBaseUrl } from '@/lib/runtime';
import { MatchState, PlayerAction, WsMessage } from '@/lib/types';

const initialState: MatchState = {
  tick: 0,
  remainingMs: 120000,
  status: 'pending',
  gridSize: 20,
  winner: null,
  settings: { agentSpeed: 'slow', obstacleDensity: 'medium', layoutTransform: false },
  human: { x: 1, y: 1, score: 0 },
  agent: { x: 18, y: 18, score: 0 },
  walls: [],
  swamps: [],
  tasks: [],
  latestEvent: 'Runner must finish all tasks and survive for 60 seconds.',
  humanStunTicks: 0,
  agentStunTicks: 0,
  agentVisionRadius: 6,
  activeEventType: null,
  eventDisplayTicks: 0,
  layoutTransformTicks: 0,
  highlightedWalls: []
};

const eventStyles: Record<string, string> = {
  boost: 'event-card event-boost border-rose-400/60 bg-rose-500/15 text-rose-50',
  freeze: 'event-card event-freeze border-cyan-400/60 bg-cyan-500/15 text-cyan-50',
  task: 'event-card border-amber-400/60 bg-amber-400/15 text-amber-50',
  transform: 'event-card event-transform border-fuchsia-400/60 bg-fuchsia-500/15 text-fuchsia-50',
  decay: 'event-card event-decay border-amber-300/60 bg-amber-500/15 text-amber-50'
};

function normalizeMatchState(state: Partial<MatchState>): MatchState {
  return {
    ...initialState,
    ...state,
    settings: {
      ...initialState.settings,
      ...state.settings
    },
    human: {
      ...initialState.human,
      ...state.human
    },
    agent: {
      ...initialState.agent,
      ...state.agent
    },
    walls: state.walls ?? initialState.walls,
    swamps: state.swamps ?? initialState.swamps,
    tasks: state.tasks ?? initialState.tasks,
    latestEvent: state.latestEvent ?? initialState.latestEvent,
    humanStunTicks: state.humanStunTicks ?? initialState.humanStunTicks,
    agentStunTicks: state.agentStunTicks ?? initialState.agentStunTicks,
    agentVisionRadius: state.agentVisionRadius ?? initialState.agentVisionRadius,
    activeEventType: state.activeEventType ?? initialState.activeEventType,
    eventDisplayTicks: state.eventDisplayTicks ?? initialState.eventDisplayTicks,
    layoutTransformTicks: state.layoutTransformTicks ?? initialState.layoutTransformTicks,
    highlightedWalls: state.highlightedWalls ?? initialState.highlightedWalls
  };
}

function BattleContent() {
  const router = useRouter();
  const params = useSearchParams();
  const matchId = params.get('matchId');
  const [state, setState] = useState<MatchState>(initialState);
  const [winner, setWinner] = useState<'human' | 'agent' | 'draw' | null>(null);
  const [error, setError] = useState<string | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const shouldReconnectRef = useRef(true);
  const [connectionReady, setConnectionReady] = useState(false);
  const modalEventActive =
    state.eventDisplayTicks > 0 && state.activeEventType && state.activeEventType !== 'task';

  const wsUrl = useMemo(() => {
    const base = getWsBaseUrl();
    return matchId ? `${base}/ws/matches/${matchId}` : null;
  }, [matchId]);

  const sendAction = (action: PlayerAction) => {
    if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) {
      setError('Match connection is not ready');
      return;
    }
    socketRef.current.send(JSON.stringify({ type: 'PLAYER_ACTION', payload: { action } }));
  };

  useEffect(() => {
    if (!wsUrl) return;
    shouldReconnectRef.current = true;
    let reconnectAttempts = 0;

    const clearReconnectTimer = () => {
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
    };

    const connect = () => {
      const ws = new WebSocket(wsUrl);
      socketRef.current = ws;
      setConnectionReady(false);

      ws.onopen = () => {
        reconnectAttempts = 0;
        setConnectionReady(true);
        setError(null);
      };

      ws.onmessage = (event) => {
        const message = JSON.parse(event.data) as WsMessage;
        if (message.type === 'MATCH_STATE') {
          setState(normalizeMatchState(message.payload));
          if (message.payload.status === 'finished') {
            shouldReconnectRef.current = false;
          }
        } else if (message.type === 'MATCH_RESULT') {
          setWinner(message.payload.winner);
          shouldReconnectRef.current = false;
        } else if (message.type === 'ERROR') {
          setError(message.payload.message);
        }
      };

      ws.onerror = () => {
        setError('Match connection lost. Retrying...');
      };

      ws.onclose = () => {
        socketRef.current = null;
        setConnectionReady(false);

        if (!shouldReconnectRef.current) {
          return;
        }

        reconnectAttempts += 1;
        const delay = Math.min(1000 * reconnectAttempts, 3000);
        setError(`Match connection lost. Retrying in ${Math.ceil(delay / 1000)}s...`);
        clearReconnectTimer();
        reconnectTimerRef.current = setTimeout(connect, delay);
      };
    };

    connect();

    return () => {
      shouldReconnectRef.current = false;
      clearReconnectTimer();
      socketRef.current?.close();
      socketRef.current = null;
      setConnectionReady(false);
    };
  }, [wsUrl]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const map: Record<string, PlayerAction> = {
        ArrowUp: 'up',
        ArrowDown: 'down',
        ArrowLeft: 'left',
        ArrowRight: 'right',
        w: 'up',
        s: 'down',
        a: 'left',
        d: 'right'
      };
      const action = map[event.key];
      if (!action) {
        return;
      }
      event.preventDefault();
      sendAction(action);
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  if (!matchId) {
    return (
      <main className="mx-auto flex min-h-screen max-w-4xl items-center justify-center px-6 text-center">
        <div>
          <div className="text-xl font-semibold">Missing match ID.</div>
          <button
            onClick={() => router.push('/')}
            className="mt-4 rounded-xl bg-sky-500 px-4 py-2 font-semibold text-slate-950"
          >
            Back home
          </button>
        </div>
      </main>
    );
  }

  return (
    <main className="mx-auto min-h-screen max-w-7xl px-6 py-8">
      <div className="mb-6 flex items-center justify-between gap-4">
        <div>
          <div className="text-sm uppercase tracking-[0.3em] text-slate-400">Live Match</div>
          <h1 className="mt-2 text-3xl font-bold">Match {matchId}</h1>
        </div>
        <button
          onClick={() => router.push('/')}
          className="rounded-2xl border border-slate-700 px-4 py-2 text-sm font-medium text-slate-200 hover:bg-slate-900"
        >
          New match
        </button>
      </div>

      <div className={`space-y-6 transition ${modalEventActive ? 'pointer-events-none blur-sm' : ''}`}>
        <ScorePanel state={state} winner={winner} />
        {error ? (
          <div className="rounded-2xl border border-rose-800 bg-rose-950/40 p-4 text-rose-200">{error}</div>
        ) : null}
        {!connectionReady ? (
          <div className="rounded-2xl border border-amber-800 bg-amber-950/30 p-4 text-amber-200">
            Connecting to match server...
          </div>
        ) : null}
        <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
          <Arena state={state} />
          <div className="space-y-6">
            <ControlHint />
            <TouchControls disabled={!connectionReady || state.status !== 'running'} onAction={sendAction} />
          </div>
        </div>
      </div>
      {modalEventActive ? (
        <div className="pointer-events-none fixed inset-0 z-[200] flex items-center justify-center bg-slate-950/70 backdrop-blur-md">
          <div className={`w-[min(92vw,560px)] rounded-[2rem] border px-8 py-8 text-center shadow-[0_0_80px_rgba(15,23,42,0.55)] ${eventStyles[state.activeEventType!]}`}>
            <div className="text-xs uppercase tracking-[0.45em] opacity-70">Event Triggered</div>
            <div className="mt-4 text-4xl font-black leading-tight">{state.latestEvent}</div>
            <div className="mt-4 text-base opacity-90">
              {state.activeEventType === 'freeze' && 'The whole arena freezes while the chaser is locked in ice.'}
              {state.activeEventType === 'boost' && 'The whole arena pauses while the chaser charges up a burst.'}
              {state.activeEventType === 'transform' && 'The whole arena pauses while the surviving walls re-form.'}
              {state.activeEventType === 'decay' && 'The whole arena pauses while the highlighted walls collapse.'}
            </div>
            <div className="mt-5 text-sm uppercase tracking-[0.35em] opacity-70">
              Match Paused · {Math.ceil(state.eventDisplayTicks / 10)}s
            </div>
          </div>
        </div>
      ) : null}
    </main>
  );
}

function BattleLoading() {
  return (
    <main className="mx-auto flex min-h-screen max-w-4xl items-center justify-center px-6 text-center">
      <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6 text-slate-300">
        Loading match...
      </div>
    </main>
  );
}

export default function BattlePage() {
  return (
    <Suspense fallback={<BattleLoading />}>
      <BattleContent />
    </Suspense>
  );
}
