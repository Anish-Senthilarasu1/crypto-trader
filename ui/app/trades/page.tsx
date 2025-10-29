'use client'

import { useEffect, useState } from 'react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Trade {
  trade_id: string
  symbol: string
  side: string
  entry_price: string
  exit_price: string
  quantity: string
  pnl: string
  pnl_percent: string
  entry_time: string
  exit_time: string
}

export default function Trades() {
  const [trades, setTrades] = useState<Trade[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<'all' | 'wins' | 'losses'>('all')

  useEffect(() => {
    fetchTrades()
    const interval = setInterval(fetchTrades, 10000) // Refresh every 10s
    return () => clearInterval(interval)
  }, [])

  const fetchTrades = async () => {
    try {
      const res = await fetch(`${API_URL}/api/metrics/trades?limit=100`)
      const data = await res.json()
      setTrades(data)
      setLoading(false)
    } catch (error) {
      console.error('Error fetching trades:', error)
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

  const filteredTrades = trades.filter((trade) => {
    const pnl = parseFloat(trade.pnl)
    if (filter === 'wins') return pnl > 0
    if (filter === 'losses') return pnl < 0
    return true
  })

  const stats = {
    total: trades.length,
    wins: trades.filter((t) => parseFloat(t.pnl) > 0).length,
    losses: trades.filter((t) => parseFloat(t.pnl) < 0).length,
    totalPnl: trades.reduce((sum, t) => sum + parseFloat(t.pnl), 0),
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-3xl font-bold text-gray-900">Trade History</h2>
        <p className="mt-1 text-sm text-gray-500">
          All closed trades
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-4">
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <dt className="text-sm font-medium text-gray-500 truncate">
              Total Trades
            </dt>
            <dd className="mt-1 text-3xl font-semibold text-gray-900">
              {stats.total}
            </dd>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <dt className="text-sm font-medium text-gray-500 truncate">
              Wins
            </dt>
            <dd className="mt-1 text-3xl font-semibold text-green-600">
              {stats.wins}
            </dd>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <dt className="text-sm font-medium text-gray-500 truncate">
              Losses
            </dt>
            <dd className="mt-1 text-3xl font-semibold text-red-600">
              {stats.losses}
            </dd>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <dt className="text-sm font-medium text-gray-500 truncate">
              Total P&L
            </dt>
            <dd className={`mt-1 text-3xl font-semibold ${stats.totalPnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {stats.totalPnl >= 0 ? '+' : ''}${stats.totalPnl.toFixed(2)}
            </dd>
          </div>
        </div>
      </div>

      {/* Filter */}
      <div className="bg-white shadow rounded-lg p-4">
        <div className="flex space-x-2">
          <button
            onClick={() => setFilter('all')}
            className={`px-4 py-2 text-sm font-medium rounded-md ${
              filter === 'all'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            All
          </button>
          <button
            onClick={() => setFilter('wins')}
            className={`px-4 py-2 text-sm font-medium rounded-md ${
              filter === 'wins'
                ? 'bg-green-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Wins
          </button>
          <button
            onClick={() => setFilter('losses')}
            className={`px-4 py-2 text-sm font-medium rounded-md ${
              filter === 'losses'
                ? 'bg-red-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Losses
          </button>
        </div>
      </div>

      {/* Trades Table */}
      <div className="bg-white shadow rounded-lg">
        {filteredTrades.length > 0 ? (
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
                    Entry
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Exit
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    P&L
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Entry Time
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Exit Time
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredTrades.map((trade) => {
                  const pnl = parseFloat(trade.pnl)
                  const pnlPct = parseFloat(trade.pnl_percent)

                  return (
                    <tr key={trade.trade_id}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {trade.symbol}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        <span
                          className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${
                            trade.side === 'buy' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                          }`}
                        >
                          {trade.side.toUpperCase()}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {parseFloat(trade.quantity).toFixed(4)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        ${parseFloat(trade.entry_price).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        ${parseFloat(trade.exit_price).toLocaleString()}
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
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {new Date(trade.entry_time).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {trade.exit_time ? new Date(trade.exit_time).toLocaleString() : '-'}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="px-6 py-12 text-center text-gray-500">
            {filter === 'all' ? 'No trades yet' : `No ${filter} to display`}
          </div>
        )}
      </div>
    </div>
  )
}
