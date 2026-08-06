import { MarketIndices } from '@/components/dashboard/market-indices';
import { MarketChart } from '@/components/dashboard/market-chart';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { RecentAlerts } from '@/components/dashboard/recent-alerts';
import { PerformanceSummary } from '@/components/dashboard/performance-summary';
import { OptionChainAnalysis } from '@/components/dashboard/option-chain';

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Real-time market overview and AI-powered insights
        </p>
      </div>

      {/* Market Indices */}
      <MarketIndices />

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>NIFTY 50 - Intraday Chart</CardTitle>
          </CardHeader>
          <CardContent>
            <MarketChart symbol="NIFTY" />
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

      {/* Option Chain Section */}
      <Card>
        <CardHeader>
          <CardTitle>NIFTY Option Chain</CardTitle>
        </CardHeader>
        <CardContent>
          <OptionChainAnalysis symbol="NIFTY" />
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>BANKNIFTY - Intraday Chart</CardTitle>
          </CardHeader>
          <CardContent>
            <MarketChart symbol="BANKNIFTY" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Market Stats</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">Market Breadth</p>
                <div className="flex items-center gap-2">
                  <span className="text-2xl font-bold text-green-600">1,247</span>
                  <span className="text-sm text-green-600">Advances</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-2xl font-bold text-red-600">892</span>
                  <span className="text-sm text-red-600">Declines</span>
                </div>
              </div>
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">F&O Turnover</p>
                <p className="text-2xl font-bold">₹4.2L Cr</p>
                <p className="text-xs text-green-600">+12.5% vs yesterday</p>
              </div>
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">NIFTY PCR</p>
                <p className="text-2xl font-bold">0.87</p>
                <p className="text-xs text-muted-foreground">Open Interest Ratio</p>
              </div>
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">India VIX</p>
                <p className="text-2xl font-bold">14.56</p>
                <p className="text-xs text-red-600">-5.09%</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
