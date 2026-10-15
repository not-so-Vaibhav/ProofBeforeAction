import React, { useEffect, useState } from 'react';
import { Activity, CheckCircle2, XCircle, RefreshCw, Shield, GitBranch, FlaskConical, ArrowRight } from 'lucide-react';
import { fetchHealth, type HealthResponse } from './services/api';

export const App: React.FC = () => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  const checkBackendHealth = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchHealth();
      setHealth(data);
      setLastChecked(new Date());
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to connect to backend server');
      }
      setHealth(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkBackendHealth();
  }, []);

  return (
    <div className="min-h-screen bg-bg text-text flex flex-col font-sans">
      {/* Top Navigation Bar */}
      <header className="border-b border-border bg-surface px-6 py-4 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-surface-2 border border-border rounded-input flex items-center justify-center">
            <Shield className="w-6 h-6 text-accent" />
          </div>
          <div>
            <h1 className="text-lg font-semibold tracking-tight text-text">
              ProofBeforeAction
            </h1>
            <p className="text-xs text-text-muted">
              Pre-Execution Consequence Analysis Engine
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          <span className="text-xs font-mono px-3 py-1 bg-surface-2 border border-border rounded-badge text-text-muted">
            Phase P0: Foundation
          </span>
          <div className="flex items-center space-x-2">
            <span
              className={`w-2.5 h-2.5 rounded-full ${
                health?.status === 'ok' ? 'bg-allow animate-pulse' : 'bg-block'
              }`}
            />
            <span className="text-xs font-medium">
              {health?.status === 'ok' ? 'Backend Live' : 'Backend Offline'}
            </span>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-5xl w-full mx-auto p-6 md:p-8 space-y-8">
        {/* Hero Section */}
        <div className="space-y-3">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-pill bg-surface-2 border border-border text-xs text-accent-soft">
            <span>VIT CODE APEX 3.0</span>
            <span>•</span>
            <span>Open Innovation</span>
          </div>
          <h2 className="text-3xl font-bold tracking-tight text-text">
            Understand the consequences before you commit to the action.
          </h2>
          <p className="text-base text-text-muted max-w-2xl leading-relaxed">
            ProofBeforeAction maps proposed changes onto a dependency graph, proves likely failures
            via disposable in-memory replay, grades findings by evidence tiers, and provides a
            self-verified safer alternative.
          </p>
        </div>

        {/* Backend Health Check Verification Panel */}
        <section className="bg-surface border border-border rounded-card p-6 shadow-sm">
          <div className="flex items-center justify-between border-b border-border pb-4 mb-4">
            <div className="flex items-center space-x-2.5">
              <Activity className="w-5 h-5 text-accent" />
              <h3 className="text-base font-semibold text-text">
                Backend System Verification (/health)
              </h3>
            </div>
            <button
              onClick={checkBackendHealth}
              disabled={loading}
              className="inline-flex items-center space-x-2 px-3 py-1.5 text-xs font-medium bg-surface-2 hover:bg-border text-text border border-border rounded-input transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              <span>{loading ? 'Checking...' : 'Refresh Status'}</span>
            </button>
          </div>

          {loading && !health && !error && (
            <div className="py-8 flex flex-col items-center justify-center space-y-3 text-text-muted">
              <RefreshCw className="w-6 h-6 animate-spin text-accent" />
              <p className="text-sm">Connecting to backend at http://localhost:8000/health...</p>
            </div>
          )}

          {health && (
            <div className="space-y-4">
              <div className="flex items-center space-x-3 p-4 bg-surface-2/60 border border-allow/30 rounded-input">
                <CheckCircle2 className="w-6 h-6 text-allow flex-shrink-0" />
                <div className="flex-1">
                  <div className="flex items-center space-x-2">
                    <span className="font-semibold text-sm text-allow">
                      Health Check Passed
                    </span>
                    <span className="text-xs font-mono text-text-muted bg-surface px-2 py-0.5 rounded border border-border">
                      HTTP 200 OK
                    </span>
                  </div>
                  <p className="text-xs text-text-muted mt-1">
                    Connected to FastAPI server. Ready for Phase P1 engine modules.
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 font-mono text-xs">
                <div className="p-3 bg-surface-2 border border-border rounded-input">
                  <span className="text-text-muted block text-[11px] mb-1">STATUS</span>
                  <span className="text-allow font-semibold uppercase">{health.status}</span>
                </div>
                <div className="p-3 bg-surface-2 border border-border rounded-input">
                  <span className="text-text-muted block text-[11px] mb-1">SERVICE</span>
                  <span className="text-text font-semibold">{health.service}</span>
                </div>
                <div className="p-3 bg-surface-2 border border-border rounded-input">
                  <span className="text-text-muted block text-[11px] mb-1">VERSION</span>
                  <span className="text-accent-soft font-semibold">v{health.version}</span>
                </div>
              </div>

              {lastChecked && (
                <p className="text-[11px] font-mono text-text-muted text-right">
                  Last verified: {lastChecked.toLocaleTimeString()}
                </p>
              )}
            </div>
          )}

          {error && (
            <div className="p-4 bg-surface-2/60 border border-block/30 rounded-input space-y-3">
              <div className="flex items-center space-x-3">
                <XCircle className="w-6 h-6 text-block flex-shrink-0" />
                <div>
                  <h4 className="font-semibold text-sm text-block">Connection Failed</h4>
                  <p className="text-xs text-text-muted mt-0.5">{error}</p>
                </div>
              </div>
              <p className="text-xs text-text-muted font-mono bg-bg/70 p-2.5 rounded border border-border">
                Target: http://localhost:8000/health • Ensure uvicorn is running: uvicorn main:app --reload --port 8000
              </p>
            </div>
          )}
        </section>

        {/* Core Architecture Feature Cards */}
        <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-5 bg-surface border border-border rounded-card space-y-2.5">
            <div className="w-8 h-8 rounded-input bg-surface-2 border border-border flex items-center justify-center text-accent">
              <GitBranch className="w-4 h-4" />
            </div>
            <h4 className="text-sm font-semibold text-text">1. Blast Radius Analysis</h4>
            <p className="text-xs text-text-muted leading-relaxed">
              Builds a NetworkX dependency graph with extracted, declared, and modeled provenance to trace downstream impact.
            </p>
          </div>

          <div className="p-5 bg-surface border border-border rounded-card space-y-2.5">
            <div className="w-8 h-8 rounded-input bg-surface-2 border border-border flex items-center justify-center text-tier-proven">
              <FlaskConical className="w-4 h-4" />
            </div>
            <h4 className="text-sm font-semibold text-text">2. Proof by Replay</h4>
            <p className="text-xs text-text-muted leading-relaxed">
              Replays migrations on disposable in-memory SQLite instances to capture real runtime errors, producing REPRODUCED evidence.
            </p>
          </div>

          <div className="p-5 bg-surface border border-border rounded-card space-y-2.5">
            <div className="w-8 h-8 rounded-input bg-surface-2 border border-border flex items-center justify-center text-allow">
              <ArrowRight className="w-4 h-4" />
            </div>
            <h4 className="text-sm font-semibold text-text">3. Verified Remediation</h4>
            <p className="text-xs text-text-muted leading-relaxed">
              Recommends safe multistep migrations and verifies the entire sequence by re-running the engine on each step.
            </p>
          </div>
        </section>

        {/* Design System Tokens Verification */}
        <section className="p-4 bg-surface/50 border border-border rounded-card flex flex-wrap items-center justify-between gap-3 text-xs">
          <span className="text-text-muted font-medium">Design Tokens Verified:</span>
          <div className="flex flex-wrap items-center gap-2 font-mono text-[11px]">
            <span className="px-2.5 py-1 bg-surface-2 border border-border rounded-badge text-text">surface</span>
            <span className="px-2.5 py-1 bg-accent/20 border border-accent/40 rounded-badge text-accent-soft">accent</span>
            <span className="px-2.5 py-1 bg-allow/20 border border-allow/40 rounded-badge text-allow">ALLOW</span>
            <span className="px-2.5 py-1 bg-review/20 border border-review/40 rounded-badge text-review">REVIEW</span>
            <span className="px-2.5 py-1 bg-block/20 border border-block/40 rounded-badge text-block">BLOCK</span>
            <span className="px-2.5 py-1 bg-tier-proven/20 border border-tier-proven/40 rounded-badge text-tier-proven">PROVEN</span>
            <span className="px-2.5 py-1 bg-tier-inferred/20 border border-tier-inferred/40 rounded-badge text-tier-inferred">INFERRED</span>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-border bg-surface px-6 py-4 text-center text-xs text-text-muted">
        ProofBeforeAction • Consequence Analysis Engine • VIT CODE APEX 3.0
      </footer>
    </div>
  );
};

export default App;
