'use client'

import { useEffect, useState } from 'react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Status {
  worker_enabled: boolean
  kill_switch_active: boolean
  trading_enabled: boolean
  daily_pnl: number
  daily_pnl_pct: number
  max_daily_loss_pct: number
  symbol_whitelist: string[]
}

interface Position {
  symbol: string
  side: string
  quantity: string
  entry_price: string
  current_price: string
  unrealized_pnl: string
  unrealized_pnl_pct: string
}

export default function LiveTrading() {
  const [status, setStatus] = useState<Status | null>(null)
  const [positions, setPositions] = useState<Position[]>([])
  const [loading, setLoading] = useState(true)
  const [haltReason, setHaltReason] = useState('')

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 5000) // Refresh every 5s
    return () => clearInterval(interval)
  }, [])

  const fetchData = async () => {
    try {
      // Fetch status
      const statusRes = await fetch(`${API_URL}/api/status`)
      const statusData = await statusRes.json()
      setStatus(statusData)

      // Fetch positions
      const positionsRes = await fetch(`${API_URL}/api/metrics/positions`)
      const positionsData = await positionsRes.json()
      setPositions(positionsData)

      setLoading(false)
    } catch (error) {
      console.error('Error fetching data:', error)
      setLoading(false)
    }
  }

  const activateKillSwitch = async () => {
    const reason = haltReason || 'Manual halt from UI'

    try {
      await fetch(`${API_URL}/api/halt`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason }),
      })
      fetchData()
      setHaltReason('')
    } catch (error) {
      console.error('Error activating kill switch:', error)
      alert('Failed to activate kill switch')
    }
  }

  const resumeTrading = async () => {
    try {
      await fetch(`${API_URL}/api/resume`, {
        method: 'POST',
      })
      fetchData()
    } catch (error) {
      console.error('Error resuming trading:', error)
      alert('Failed to resume trading')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading...</div>
      </div>
    )
  }

  if (!status) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-red-500">Failed to load status</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-3xl font-bold text-gray-900">Live Trading</h2>
        <p className="mt-1 text-sm text-gray-500">
          Monitor positions and control trading
        </p>
      </div>

      {/* Status Cards */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-3">
        {/* Worker Status */}
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <dt className="text-sm font-medium text-gray-500 truncate">
              Worker Status
            </dt>
            <dd className="mt-1 flex items-center">
              <span
                className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                  status.worker_enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                }`}
              >
                {status.worker_enabled ? 'Enabled' : 'Disabled'}
              </span>
            </dd>
          </div>
        </div>

        {/* Kill Switch */}
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <dt className="text-sm font-medium text-gray-500 truncate">
              Kill Switch
            </dt>
            <dd className="mt-1 flex items-center">
              <span
                className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                  status.kill_switch_active ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'
                }`}
              >
                {status.kill_switch_active ? 'ACTIVE' : 'Inactive'}
              </span>
            </dd>
          </div>
        </div>

        {/* Daily P&L */}
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <dt className="text-sm font-medium text-gray-500 truncate">
              Daily P&L
            </dt>
            <dd className={`mt-1 text-2xl font-semibold ${status.daily_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {status.daily_pnl >= 0 ? '+' : ''}${status.daily_pnl.toFixed(2)}
            </dd>
            <dd className={`text-xs ${status.daily_pnl_pct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {status.daily_pnl_pct >= 0 ? '+' : ''}{status.daily_pnl_pct.toFixed(2)}%
              <span className="text-gray-500"> / -{status.max_daily_loss_pct}% limit</span>
            </dd>
          </div>
        </div>
      </div>

      {/* Control Panel */}
      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Emergency Controls</h3>

        {status.kill_switch_active ? (
          <div className="space-y-4">
            <div className="bg-red-50 border border-red-200 rounded-md p-4">
              <p className="text-sm text-red-800">
                🚨 Kill switch is ACTIVE - no new orders will be placed
              </p>
            </div>
            <button
              onClick={resumeTrading}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
            >
              Resume Trading
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            <div>
              <label htmlFor="reason" className="block text-sm font-medium text-gray-700">
                Halt Reason (optional)
              </label>
              <input
                type="text"
                id="reason"
                value={haltReason}
                onChange={(e) => setHaltReason(e.target.value)}
                placeholder="e.g., Manual halt for review"
                className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
              />
            </div>
            <button
              onClick={activateKillSwitch}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
            >
              🚨 Activate Kill Switch
            </button>
          </div>
        )}
      </div>

      {/* Positions */}
      <div className="bg-white shadow rounded-lg">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900">
            Current Positions ({positions.length})
          </h3>
        </div>

        {positions.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Symbol
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Side
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Quantity
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Entry Price
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Current Price
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Unrealized P&L
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {positions.map((position, idx) => {
                  const pnl = parseFloat(position.unrealized_pnl)
                  const pnlPct = parseFloat(position.unrealized_pnl_pct)

                  return (
                    <tr key={idx}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {position.symbol}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        <span
                          className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${
                            position.side === 'buy' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                          }`}
                        >
                          {position.side.toUpperCase()}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {parseFloat(position.quantity).toFixed(4)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        ${parseFloat(position.entry_price).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        ${parseFloat(position.current_price).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <div className={pnl >= 0 ? 'text-green-600' : 'text-red-600'}>
                          <div className="font-medium">
                            {pnl >= 0 ? '+' : ''}${pnl.toFixed(2)}
                          </div>
                          <div className="text-xs">
                            {pnlPct >= 0 ? '+' : ''}{pnlPct.toFixed(2)}%
                          </div>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="px-6 py-12 text-center text-gray-500">
            No open positions
          </div>
        )}
      </div>

      {/* Symbol Whitelist */}
      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-2">Configuration</h3>
        <div className="text-sm text-gray-500">
          <p>Symbols: {status.symbol_whitelist.join(', ')}</p>
          <p className="mt-1">Max Daily Loss: {status.max_daily_loss_pct}%</p>
        </div>
      </div>
    </div>
  )
}
