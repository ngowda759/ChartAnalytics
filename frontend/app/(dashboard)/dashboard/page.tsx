import { MarketIndices } from '@/components/dashboard/market-indices';
import { MarketChart } from '@/components/dashboard/market-chart';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { RecentAlerts } from '@/components/dashboard/recent-alerts';
import { PerformanceSummary } from '@/components/dashboard/performance-summary';

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Real-time market overview and AI-powered insights
        </p>
      </div>

      <MarketIndices />

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Market Overview</CardTitle>
          </CardHeader>
          <CardContent>
            <MarketIndices />
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Recent Alerts</CardTitle>
            </CardHeader>
            <CardContent>
              <RecentAlerts />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Performance Summary</CardTitle>
            </CardHeader>
            <CardContent>
              <PerformanceSummary />
            </CardContent>
          </Card>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>NIFTY 50 - Intraday Chart</CardTitle>
          </CardHeader>
          <CardContent>
            <MarketChart symbol="NIFTY" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>BANKNIFTY - Intraday Chart</CardTitle>
          </CardHeader>
          <CardContent>
            <MarketChart symbol="BANKNIFTY" />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
