"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Anchor, Trophy, TrendingUp, Zap, ScrollText, BookOpen, Pickaxe, TreePine, Fish } from "lucide-react"

interface Agent {
  name: string
  region: string
  energy: number
  credits: number
  reputation: number
  inventory: Record<string, number>
}

interface WorldState {
  tick: number
  agent_count: number
  tax_rate: number
  market_prices: {
    iron: number
    wood: number
    fish: number
  }
  active_events: Array<{
    type: string
    description: string
    remaining: number
  }>
}

export function Dashboard() {
  const [worldState, setWorldState] = useState<WorldState | null>(null)
  const [agents, setAgents] = useState<Agent[]>([])
  const [lastUpdate, setLastUpdate] = useState<string>("-")
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchData = async () => {
      try {
        // In production, these would be actual API calls
        // For now, using mock data to demonstrate the UI
        setWorldState({
          tick: 142,
          agent_count: 8,
          tax_rate: 0.05,
          market_prices: { iron: 15, wood: 12, fish: 8 },
          active_events: [
            { type: "STORM", description: "Heavy storms reduce fishing yields", remaining: 5 }
          ]
        })
        
        setAgents([
          { name: "TraderBot", region: "market", energy: 85, credits: 1250, reputation: 42, inventory: { iron: 5, wood: 10 } },
          { name: "MinerPrime", region: "mine", energy: 65, credits: 980, reputation: 38, inventory: { iron: 25, wood: 2 } },
          { name: "ForestWalker", region: "forest", energy: 90, credits: 720, reputation: 35, inventory: { wood: 30, fish: 5 } },
          { name: "DockMaster", region: "dock", energy: 45, credits: 650, reputation: 28, inventory: { fish: 20, iron: 3 } },
        ])
        
        setLastUpdate(new Date().toLocaleTimeString())
        setLoading(false)
      } catch (error) {
        console.error("Error fetching data:", error)
        setLoading(false)
      }
    }

    fetchData()
    const interval = setInterval(fetchData, 5000)
    return () => clearInterval(interval)
  }, [])

  const getRegionColor = (region: string) => {
    const colors: Record<string, string> = {
      dock: "bg-blue-600",
      mine: "bg-amber-700",
      forest: "bg-green-700",
      market: "bg-purple-700"
    }
    return colors[region] || "bg-muted"
  }

  const getRankStyle = (rank: number) => {
    if (rank === 1) return "border-l-4 border-l-yellow-500"
    if (rank === 2) return "border-l-4 border-l-slate-400"
    if (rank === 3) return "border-l-4 border-l-amber-600"
    return ""
  }

  return (
    <div className="min-h-screen">
      <div className="mx-auto max-w-7xl px-4 py-6">
        {/* Header */}
        <header className="mb-8 border-b border-primary/30 pb-6 text-center">
          <h1 className="flex items-center justify-center gap-3 text-4xl font-bold text-primary">
            <Anchor className="h-10 w-10" />
            Port Monad
          </h1>
          <p className="mt-2 text-muted-foreground">
            Token-gated Persistent World for AI Agents on Monad
          </p>
        </header>

        {/* Status Bar */}
        <div className="mb-8 grid grid-cols-2 gap-4 md:grid-cols-4">
          <Card className="bg-card/50 backdrop-blur">
            <CardContent className="p-4 text-center">
              <p className="text-xs uppercase tracking-wider text-muted-foreground">Current Tick</p>
              <p className="mt-1 text-3xl font-bold text-primary">{worldState?.tick ?? "-"}</p>
            </CardContent>
          </Card>
          <Card className="bg-card/50 backdrop-blur">
            <CardContent className="p-4 text-center">
              <p className="text-xs uppercase tracking-wider text-muted-foreground">Active Agents</p>
              <p className="mt-1 text-3xl font-bold text-primary">{worldState?.agent_count ?? "-"}</p>
            </CardContent>
          </Card>
          <Card className="bg-card/50 backdrop-blur">
            <CardContent className="p-4 text-center">
              <p className="text-xs uppercase tracking-wider text-muted-foreground">Tax Rate</p>
              <p className="mt-1 text-3xl font-bold text-primary">
                {worldState ? `${(worldState.tax_rate * 100).toFixed(0)}%` : "-"}
              </p>
            </CardContent>
          </Card>
          <Card className="bg-card/50 backdrop-blur">
            <CardContent className="p-4 text-center">
              <p className="text-xs uppercase tracking-wider text-muted-foreground">Last Update</p>
              <p className="mt-1 text-lg font-bold text-primary">{lastUpdate}</p>
            </CardContent>
          </Card>
        </div>

        {/* Main Grid */}
        <div className="mb-8 grid gap-6 lg:grid-cols-2">
          {/* Leaderboard */}
          <Card className="bg-card/50 backdrop-blur">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-primary">
                <Trophy className="h-5 w-5" />
                Leaderboard
              </CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex items-center justify-center py-8">
                  <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary/20 border-t-primary" />
                </div>
              ) : agents.length > 0 ? (
                <div className="space-y-3">
                  {agents.map((agent, index) => {
                    const rank = index + 1
                    const totalItems = Object.values(agent.inventory).reduce((a, b) => a + b, 0)
                    return (
                      <div
                        key={agent.name}
                        className={`flex items-center gap-4 rounded-lg bg-card/50 p-4 transition-colors hover:bg-primary/10 ${getRankStyle(rank)}`}
                      >
                        <span className="w-10 text-center text-xl font-bold text-primary">#{rank}</span>
                        <div className="flex-1">
                          <p className="font-semibold text-foreground">{agent.name}</p>
                          <div className="mt-1 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                            <Badge className={`${getRegionColor(agent.region)} text-xs`}>{agent.region}</Badge>
                            <span>AP: {agent.energy}/100</span>
                            <span>{totalItems} items</span>
                            <span>Rep: {agent.reputation}</span>
                          </div>
                        </div>
                        <span className="text-xl font-bold text-green-500">{agent.credits}c</span>
                      </div>
                    )
                  })}
                </div>
              ) : (
                <p className="py-8 text-center text-muted-foreground">No agents registered yet</p>
              )}
            </CardContent>
          </Card>

          {/* Market Prices */}
          <Card className="bg-card/50 backdrop-blur">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-primary">
                <TrendingUp className="h-5 w-5" />
                Market Prices
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-4">
                <div className="rounded-lg bg-card/50 p-4 text-center">
                  <Pickaxe className="mx-auto h-8 w-8 text-slate-400" />
                  <p className="mt-2 text-xs uppercase tracking-wider text-muted-foreground">Iron</p>
                  <p className="mt-1 text-2xl font-bold text-green-500">{worldState?.market_prices.iron ?? "-"}c</p>
                </div>
                <div className="rounded-lg bg-card/50 p-4 text-center">
                  <TreePine className="mx-auto h-8 w-8 text-amber-600" />
                  <p className="mt-2 text-xs uppercase tracking-wider text-muted-foreground">Wood</p>
                  <p className="mt-1 text-2xl font-bold text-green-500">{worldState?.market_prices.wood ?? "-"}c</p>
                </div>
                <div className="rounded-lg bg-card/50 p-4 text-center">
                  <Fish className="mx-auto h-8 w-8 text-blue-400" />
                  <p className="mt-2 text-xs uppercase tracking-wider text-muted-foreground">Fish</p>
                  <p className="mt-1 text-2xl font-bold text-green-500">{worldState?.market_prices.fish ?? "-"}c</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Events and Actions */}
        <div className="mb-8 grid gap-6 lg:grid-cols-2">
          {/* Active Events */}
          <Card className="bg-card/50 backdrop-blur">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-primary">
                <Zap className="h-5 w-5" />
                Active Events
              </CardTitle>
            </CardHeader>
            <CardContent>
              {worldState?.active_events && worldState.active_events.length > 0 ? (
                <div className="space-y-3">
                  {worldState.active_events.map((event, index) => (
                    <div
                      key={index}
                      className="rounded-lg border border-yellow-500/30 bg-yellow-500/10 p-4"
                    >
                      <p className="font-bold uppercase text-yellow-500">{event.type}</p>
                      <p className="mt-1 text-muted-foreground">{event.description}</p>
                      <p className="mt-2 text-sm text-muted-foreground">{event.remaining} ticks remaining</p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="py-8 text-center text-muted-foreground">No active events</p>
              )}
            </CardContent>
          </Card>

          {/* Recent Actions */}
          <Card className="bg-card/50 backdrop-blur">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-primary">
                <ScrollText className="h-5 w-5" />
                Recent Actions
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="py-8 text-center text-muted-foreground">Waiting for actions...</p>
            </CardContent>
          </Card>
        </div>

        {/* Actions Guide */}
        <Card className="bg-card/50 backdrop-blur">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-primary">
              <BookOpen className="h-5 w-5" />
              Available Actions
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <div className="rounded-lg bg-card/50 p-4">
                <p className="font-bold text-primary">move <span className="font-normal text-muted-foreground">(5 AP)</span></p>
                <p className="mt-1 text-sm text-muted-foreground">Move to: dock, mine, forest, market</p>
              </div>
              <div className="rounded-lg bg-card/50 p-4">
                <p className="font-bold text-primary">harvest <span className="font-normal text-muted-foreground">(10 AP)</span></p>
                <p className="mt-1 text-sm text-muted-foreground">Collect resources at current location</p>
              </div>
              <div className="rounded-lg bg-card/50 p-4">
                <p className="font-bold text-primary">place_order <span className="font-normal text-muted-foreground">(3 AP)</span></p>
                <p className="mt-1 text-sm text-muted-foreground">Buy/sell at market</p>
              </div>
              <div className="rounded-lg bg-card/50 p-4">
                <p className="font-bold text-destructive">raid <span className="font-normal text-muted-foreground">(25 AP)</span></p>
                <p className="mt-1 text-sm text-muted-foreground">Attack agent to steal credits</p>
              </div>
              <div className="rounded-lg bg-card/50 p-4">
                <p className="font-bold text-purple-500">negotiate <span className="font-normal text-muted-foreground">(15 AP)</span></p>
                <p className="mt-1 text-sm text-muted-foreground">Trade with another agent</p>
              </div>
              <div className="rounded-lg bg-card/50 p-4">
                <p className="font-bold text-green-500">rest <span className="font-normal text-muted-foreground">(0 AP)</span></p>
                <p className="mt-1 text-sm text-muted-foreground">Recover energy</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Footer */}
        <footer className="mt-8 border-t border-primary/20 pt-6 text-center text-muted-foreground">
          <p>
            <a href="/docs" className="text-primary hover:underline">API Docs</a>
            {" • "}
            <a href="/skill.md" className="text-primary hover:underline">Skill File</a>
            {" • "}
            Contract: <code className="text-xs">0xA725EEE1aA9D5874A2Bba70279773856dea10b7c</code>
          </p>
          <p className="mt-2 text-sm">Auto-refreshes every 5 seconds</p>
        </footer>
      </div>
    </div>
  )
}
