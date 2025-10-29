'use client'

import { useEffect, useState } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Metrics {
  starting_equity: number
  ending_equity: number
  total_pnl: number
  total_pnl_pct: number
  num_trades: number
  num_wins: number
  num_losses: number
  win_rate: number
  max_drawdown_pct: number
}

interface EquityPoint {
  timestamp: string
  equity: number
}

export default function Dashboard() {
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [equityCurve, setEquityCurve] = useState<EquityPoint[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 30000) // Refresh every 30s
    return () => clearInterval(interval)
  }, [])

  const fetchData = async () => {
    try {
      // Fetch metrics
      const metricsRes = await fetch(`${API_URL}/api/metrics`)
      const metricsData = await metricsRes.json()
      setMetrics(metricsData)

      // Fetch equity curve
      const equityRes = await fetch(`${API_URL}/api/metrics/equity?hours=168`)
      const equityData = await equityRes.json()
      setEquityCurve(equityData.data || [])

      setLoading(false)
    } catch (error) {
      console.error('Error fetching data:', error)
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading...</div>
      </div>
    )
  }

  if (!metrics) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-red-500">Failed to load metrics</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-3xl font-bold text-gray-900">Dashboard</h2>
        <p className="mt-1 text-sm text-gray-500">
          Paper trading performance overview
        </p>
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {/* Equity */}
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-1">
                <dt className="text-sm font-medium text-gray-500 truncate">
                  Current Equity
                </dt>
                <dd className="mt-1 text-3xl font-semibold text-gray-900">
                  ${metrics.ending_equity.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </dd>
              </div>
            </div>
          </div>
        </div>

        {/* Total P&L */}
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-1">
                <dt className="text-sm font-medium text-gray-500 truncate">
                  Total P&L
                </dt>
                <dd className={`mt-1 text-3xl font-semibold ${metrics.total_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {metrics.total_pnl >= 0 ? '+' : ''}${metrics.total_pnl.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </dd>
                <dd className={`text-sm ${metrics.total_pnl_pct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {metrics.total_pnl_pct >= 0 ? '+' : ''}{metrics.total_pnl_pct.toFixed(2)}%
                </dd>
              </div>
            </div>
          </div>
        </div>

        {/* Win Rate */}
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-1">
                <dt className="text-sm font-medium text-gray-500 truncate">
                  Win Rate
                </dt>
                <dd className="mt-1 text-3xl font-semibold text-gray-900">
                  {metrics.win_rate.toFixed(1)}%
                </dd>
                <dd className="text-sm text-gray-500">
                  {metrics.num_wins}W / {metrics.num_losses}L
                </dd>
              </div>
            </div>
          </div>
        </div>

        {/* Max Drawdown */}
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-1">
                <dt className="text-sm font-medium text-gray-500 truncate">
                  Max Drawdown
                </dt>
                <dd className="mt-1 text-3xl font-semibold text-red-600">
                  -{metrics.max_drawdown_pct.toFixed(2)}%
                </dd>
                <dd className="text-sm text-gray-500">
                  {metrics.num_trades} trades
                </dd>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Equity Curve */}
      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Equity Curve</h3>
        {equityCurve.length > 0 ? (
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={equityCurve}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="timestamp"
                tickFormatter={(value) => new Date(value).toLocaleDateString()}
              />
              <YAxis
                domain={['auto', 'auto']}
                tickFormatter={(value) => `$${value.toLocaleString()}`}
              />
              <Tooltip
                formatter={(value: number) => [`$${value.toLocaleString()}`, 'Equity']}
                labelFormatter={(label) => new Date(label).toLocaleString()}
              />
              <Line
                type="monotone"
                dataKey="equity"
                stroke="#2563eb"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex items-center justify-center h-64 text-gray-500">
            No equity data available yet. Start trading to see your performance.
          </div>
        )}
      </div>
    </div>
  )
}
