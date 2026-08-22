'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { RefreshCw, Users, Scale, Target, ShieldAlert, Loader2, Fish } from 'lucide-react';
import { agentAnalysisApi } from '@/lib/api';
import { formatISTDateTime } from '@/lib/utils';
import { toast } from 'sonner';

interface DebateTurn {
  speaker: string;
  stance: string;
  argument: string;
  score: number;
}

interface AnalystReport {
  role: string;
  summary: string;
  score: number;
  key_points: string[];
}

interface ResearchPlan {
  recommendation: string;
  rationale: string;
  strategic_actions: string;
}

interface TraderProposal {
  action: string;
  reasoning: string;
  entry_price: number | null;
  stop_loss: number | null;
  position_sizing: string | null;
}

interface PortfolioDecision {
  rating: string;
  executive_summary: string;
  investment_thesis: string;
  price_target: number | null;
  time_horizon: string | null;
}

interface SwarmPredictionSummary {
  direction: 'bullish' | 'bearish' | 'neutral';
  conviction: number;
  predicted_change_percent: number;
  target_price?: number | null;
  confidence: number;
}

interface DebateResult {
  turns: DebateTurn[];
  winner: string;
  summary: string;
}

interface AgentAnalysisResult {
  symbol: string;
  name: string | null;
  timestamp: string;
  analysts: AnalystReport[];
  investment_debate: DebateResult;
  research_plan: ResearchPlan;
  trader_proposal: TraderProposal;
  risk_debate: DebateResult;
  final_decision: PortfolioDecision;
  confidence: number;
  prediction?: SwarmPredictionSummary | null;
}

interface AgentAnalysisList {
  total: number;
  buy_count: number;
  sell_count: number;
  hold_count: number;
  results: AgentAnalysisResult[];
  generated_at?: string;
  data_timestamp?: string | null;
  source?: string;
  is_stale?: boolean;
}

function ratingVariant(rating: string) {
  if (['Buy', 'Overweight'].includes(rating)) return 'success';
  if (['Sell', 'Underweight'].includes(rating)) return 'destructive';
  return 'secondary';
}

function actionVariant(action: string) {
  if (action === 'Buy') return 'success';
  if (action === 'Sell') return 'destructive';
  return 'secondary';
}

function predictionVariant(direction: string): 'bullish' | 'bearish' | 'neutral' {
  if (direction === 'bullish') return 'bullish';
  if (direction === 'bearish') return 'bearish';
  return 'neutral';
}

function fmt(v: number | null | undefined) {
  if (v === null || v === undefined) return '—';
  return `₹${v.toFixed(2)}`;
}

export default function AgentAnalysisPage() {
  const [selected, setSelected] = useState<AgentAnalysisResult | null>(null);

  const fetchList = async () => {
    const { data, error } = await agentAnalysisApi.list(25);
    if (error || !data) throw new Error(error || 'Failed to load agent analyses');
    return data as unknown as AgentAnalysisList;
  };

  const { data, isLoading, isError, refetch, isFetching } = useQuery<AgentAnalysisList>({
    queryKey: ['agent-analysis-list'],
    queryFn: fetchList,
  });

  const openSymbol = async (symbol: string) => {
    const { data, error } = await agentAnalysisApi.get(symbol);
    if (error || !data) {
      toast.error(error || 'Failed to load analysis');
      return;
    }
    setSelected(data as unknown as AgentAnalysisResult);
  };

  return (
    <div className="container mx-auto space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Users className="h-7 w-7 text-primary" />
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Agent Analysis</h1>
            <p className="text-sm text-muted-foreground">
              TradingAgents-style multi-agent pipeline: analysts → debate →
              research manager → trader → risk debate → portfolio manager.
            </p>
            {data?.source && (
              <p className="mt-1 text-xs text-muted-foreground">
                Source: <span className="capitalize">{data.source}</span>
                {data.is_stale && ' (stale)'}
                {data.generated_at &&
                  ` · generated ${formatISTDateTime(data.generated_at)} IST`}
              </p>
            )}
          </div>
        </div>
        <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isFetching}>
          {isFetching ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <RefreshCw className="h-4 w-4" />
          )}
          Refresh
        </Button>
      </div>

      {isLoading ? (
        <div className="flex h-64 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : isError ? (
        <Card>
          <CardContent className="p-6 text-center text-muted-foreground">
            Failed to load analyses. Try refreshing.
          </CardContent>
        </Card>
      ) : data ? (
        <>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <Card>
              <CardContent className="p-4">
                <p className="text-xs text-muted-foreground">Total</p>
                <p className="text-2xl font-bold">{data.total}</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <p className="text-xs text-muted-foreground">Buy / Overweight</p>
                <p className="text-2xl font-bold text-green-600">{data.buy_count}</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <p className="text-xs text-muted-foreground">Hold</p>
                <p className="text-2xl font-bold">{data.hold_count}</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <p className="text-xs text-muted-foreground">Underweight / Sell</p>
                <p className="text-2xl font-bold text-red-600">{data.sell_count}</p>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Watchlist Results</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="border-b bg-muted/50 text-left">
                    <tr>
                      <th className="px-4 py-2 font-medium">Symbol</th>
                      <th className="px-4 py-2 font-medium">Rating</th>
                      <th className="px-4 py-2 font-medium">Action</th>
                      <th className="px-4 py-2 font-medium">Conf.</th>
                      <th className="px-4 py-2 font-medium">Swarm</th>
                      <th className="px-4 py-2 font-medium">Target</th>
                      <th className="px-4 py-2 font-medium">Horizon</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.results.map((r) => (
                      <tr
                        key={r.symbol}
                        className="cursor-pointer border-b hover:bg-accent/50"
                        onClick={() => openSymbol(r.symbol)}
                      >
                        <td className="px-4 py-2 font-medium">
                          {r.symbol}
                          {r.name && (
                            <span className="block text-xs text-muted-foreground">
                              {r.name}
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-2">
                          <Badge variant={ratingVariant(r.final_decision.rating)}>
                            {r.final_decision.rating}
                          </Badge>
                        </td>
                        <td className="px-4 py-2">
                          <Badge variant={actionVariant(r.trader_proposal.action)}>
                            {r.trader_proposal.action}
                          </Badge>
                        </td>
                        <td className="px-4 py-2">
                          {(r.confidence * 100).toFixed(0)}%
                        </td>
                        <td className="px-4 py-2">
                          {r.prediction ? (
                            <Badge variant={predictionVariant(r.prediction.direction)}>
                              {r.prediction.predicted_change_percent >= 0 ? '+' : ''}
                              {r.prediction.predicted_change_percent.toFixed(2)}% ·{' '}
                              {r.prediction.conviction}
                            </Badge>
                          ) : (
                            '—'
                          )}
                        </td>
                        <td className="px-4 py-2">
                          {fmt(r.final_decision.price_target)}
                        </td>
                        <td className="px-4 py-2 text-xs">
                          {r.final_decision.time_horizon ?? '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </>
      ) : null}

      {selected && (
        <SymbolDetailModal result={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}

function SymbolDetailModal({
  result,
  onClose,
}: {
  result: AgentAnalysisResult;
  onClose: () => void;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={onClose}
    >
      <div
        className="max-h-[85vh] w-full max-w-3xl overflow-y-auto rounded-lg border bg-background p-6 shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-start justify-between">
          <div>
            <h2 className="text-xl font-bold">
              {result.symbol}
              {result.name && (
                <span className="ml-2 text-sm font-normal text-muted-foreground">
                  {result.name}
                </span>
              )}
            </h2>
            <p className="text-xs text-muted-foreground">
              {formatISTDateTime(result.timestamp)} IST
            </p>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose}>
            ✕
          </Button>
        </div>

        <div className="mb-4 flex flex-wrap items-center gap-2">
          <Badge variant={ratingVariant(result.final_decision.rating)}>
            Rating: {result.final_decision.rating}
          </Badge>
          <Badge variant={actionVariant(result.trader_proposal.action)}>
            Action: {result.trader_proposal.action}
          </Badge>
          <Badge variant="outline">
            Confidence: {(result.confidence * 100).toFixed(0)}%
          </Badge>
        </div>

        <Section title="Analyst Reports" icon={<Users className="h-4 w-4" />}>
          <div className="grid gap-3 md:grid-cols-2">
            {result.analysts.map((a) => (
              <div key={a.role} className="rounded-md border p-3">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-semibold">{a.role}</p>
                  <Badge variant="secondary">{a.score}</Badge>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">{a.summary}</p>
                <ul className="mt-2 list-disc space-y-0.5 pl-4 text-xs">
                  {a.key_points.map((p, i) => (
                    <li key={i}>{p}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </Section>

        <Section title="Investment Debate (Bull vs Bear)" icon={<Scale className="h-4 w-4" />}>
          <p className="mb-2 text-xs text-muted-foreground">
            Winner: <span className="font-semibold capitalize">{result.investment_debate.winner}</span> — {result.investment_debate.summary}
          </p>
          {result.investment_debate.turns.map((t, i) => (
            <div key={i} className="mb-2 rounded-md border p-2 text-xs">
              <span className="font-semibold">{t.speaker}</span>{' '}
              <Badge variant="secondary" className="ml-1">{t.score}</Badge>
              <p className="mt-1 text-muted-foreground">{t.argument}</p>
            </div>
          ))}
        </Section>

        <Section title="Research Plan" icon={<Target className="h-4 w-4" />}>
          <p className="text-sm">
            <span className="font-semibold">Recommendation:</span>{' '}
            {result.research_plan.recommendation}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            {result.research_plan.rationale}
          </p>
          <p className="mt-1 text-xs">
            <span className="font-semibold">Strategic actions:</span>{' '}
            {result.research_plan.strategic_actions}
          </p>
        </Section>

        <Section title="Trader Proposal" icon={<Target className="h-4 w-4" />}>
          <div className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
            <Field label="Action" value={result.trader_proposal.action} />
            <Field label="Entry" value={fmt(result.trader_proposal.entry_price)} />
            <Field label="Stop" value={fmt(result.trader_proposal.stop_loss)} />
            <Field label="Sizing" value={result.trader_proposal.position_sizing ?? '—'} />
          </div>
          <p className="mt-2 text-xs text-muted-foreground">
            {result.trader_proposal.reasoning}
          </p>
        </Section>

        <Section title="Risk Debate" icon={<ShieldAlert className="h-4 w-4" />}>
          <p className="mb-2 text-xs text-muted-foreground">
            Leans: <span className="font-semibold capitalize">{result.risk_debate.winner}</span> — {result.risk_debate.summary}
          </p>
          {result.risk_debate.turns.map((t, i) => (
            <div key={i} className="mb-2 rounded-md border p-2 text-xs">
              <span className="font-semibold">{t.speaker}</span>{' '}
              <Badge variant="secondary" className="ml-1">{t.score}</Badge>
              <p className="mt-1 text-muted-foreground">{t.argument}</p>
            </div>
          ))}
        </Section>

        <Section title="Portfolio Decision" icon={<Target className="h-4 w-4" />}>
          <p className="text-sm font-semibold">
            Final Rating: {result.final_decision.rating}
          </p>
          <p className="mt-1 text-sm">{result.final_decision.executive_summary}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            {result.final_decision.investment_thesis}
          </p>
          <div className="mt-2 grid grid-cols-2 gap-2 text-xs sm:grid-cols-3">
            <Field label="Price Target" value={fmt(result.final_decision.price_target)} />
            <Field label="Time Horizon" value={result.final_decision.time_horizon ?? '—'} />
          </div>
        </Section>

        {result.prediction && (
          <Section title="Swarm Forecast (MiroFish)" icon={<Fish className="h-4 w-4" />}>
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant={predictionVariant(result.prediction.direction)}>
                {result.prediction.direction}
              </Badge>
              <Badge variant="outline">
                Conviction {result.prediction.conviction}/100
              </Badge>
              <Badge variant="outline">
                {result.prediction.predicted_change_percent >= 0 ? '+' : ''}
                {result.prediction.predicted_change_percent.toFixed(2)}% expected
              </Badge>
            </div>
            <div className="mt-2 grid grid-cols-2 gap-2 text-xs sm:grid-cols-2">
              <Field
                label="Swarm Target"
                value={
                  result.prediction.target_price !== null &&
                  result.prediction.target_price !== undefined
                    ? fmt(result.prediction.target_price)
                    : '—'
                }
              />
              <Field
                label="Swarm Confidence"
                value={`${Math.round(result.prediction.confidence * 100)}%`}
              />
            </div>
          </Section>
        )}

        <p className="mt-4 text-[10px] text-muted-foreground">
          Derived from the TradingAgents-style deterministic pipeline
          (Apache-2.0, github.com/TauricResearch/TradingAgents). Educational
          only — not investment advice.
        </p>
      </div>
    </div>
  );
}

function Section({
  title,
  icon,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="mb-5">
      <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold">
        {icon}
        {title}
      </h3>
      {children}
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border p-2">
      <p className="text-[10px] uppercase text-muted-foreground">{label}</p>
      <p className="text-sm font-medium">{value}</p>
    </div>
  );
}
