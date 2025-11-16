import React, { type ReactNode, FormEvent, useCallback, useEffect, useMemo, useState } from "react";

const STORAGE_KEY = "nesco_admin_basic";

const resolveApiBase = () => {
  if (import.meta.env.VITE_BACKEND_URL) {
    return import.meta.env.VITE_BACKEND_URL as string;
  }
  if (typeof window !== "undefined") {
    return window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
      ? "http://localhost:5001"
      : window.location.origin;
  }
  return "http://localhost:5001";
};

const DEFAULT_API_BASE = resolveApiBase();

const StatCard = ({
  title,
  value,
  subtitle,
}: {
  title: string;
  value: string | number;
  subtitle?: string;
}) => (
  <div className="rounded-2xl border border-border bg-card p-6 shadow-sm">
    <p className="text-sm text-muted-foreground">{title}</p>
    <p className="mt-2 text-3xl font-semibold text-foreground">{value}</p>
    {subtitle && <p className="mt-1 text-xs text-muted-foreground">{subtitle}</p>}
  </div>
);

const SectionCard = ({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) => (
  <div className="rounded-2xl border border-border bg-card p-6 shadow-sm">
    <div className="mb-4 flex items-center justify-between">
      <h3 className="text-lg font-semibold">{title}</h3>
    </div>
    {children}
  </div>
);

type AdminStats = {
  total_users: number;
  total_meters: number;
  reminders_enabled: number;
  active_users_24h: number;
  latest_users: Array<{
    id: number;
    username: string | null;
    telegram_user_id: number;
    created_at: string | null;
  }>;
  latest_meters: Array<{
    id: number;
    name: string;
    number: string;
    owner: string;
    created_at: string | null;
  }>;
  recent_activity: Array<{
    id: number;
    meter_name: string;
    meter_number: string;
    user: string;
    balance: number;
    recorded_at: string | null;
  }>;
};

const formatDate = (value?: string | null) => {
  if (!value) return "—";
  const date = new Date(value);
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
};

const AdminDashboard = () => {
  const [username, setUsername] = useState("shuvo");
  const [password, setPassword] = useState("shuvo");
  const [authToken, setAuthToken] = useState<string | null>(() =>
    typeof window !== "undefined" ? localStorage.getItem(STORAGE_KEY) : null,
  );
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const headers = useMemo(() => {
    if (!authToken) return {};
    return {
      Authorization: `Basic ${authToken}`,
    };
  }, [authToken]);

  const fetchStats = useCallback(
    async (token?: string) => {
      const headerToken = token ?? authToken;
      if (!headerToken) return;
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(`${DEFAULT_API_BASE}/admin/api/stats`, {
          headers: { ...headers, Authorization: `Basic ${headerToken}` },
        });
        if (response.status === 401) {
          throw new Error("Unauthorized");
        }
        if (!response.ok) {
          throw new Error(`Failed to load stats (${response.status})`);
        }
        const payload = await response.json();
        setStats(payload.stats);
        if (token) {
          setAuthToken(token);
          localStorage.setItem(STORAGE_KEY, token);
        }
      } catch (err) {
        console.error(err);
        setStats(null);
        setAuthToken(null);
        localStorage.removeItem(STORAGE_KEY);
        setError("Invalid credentials or server unavailable.");
      } finally {
        setLoading(false);
      }
    },
    [authToken, headers],
  );

  useEffect(() => {
    if (authToken && !stats && !loading) {
      fetchStats();
    }
  }, [authToken, fetchStats, loading, stats]);

  const handleLogin = async (event: FormEvent) => {
    event.preventDefault();
    const token = btoa(`${username}:${password}`);
    await fetchStats(token);
  };

  const handleLogout = () => {
    setAuthToken(null);
    setStats(null);
    localStorage.removeItem(STORAGE_KEY);
  };

  if (!authToken || !stats) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-muted/40 px-4">
        <div className="w-full max-w-md rounded-2xl border border-border bg-card p-8 shadow-xl">
          <h1 className="text-2xl font-semibold">Admin Login</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Enter the protected credentials to access usage analytics.
          </p>
          <form className="mt-6 space-y-4" onSubmit={handleLogin}>
            <div>
              <label className="text-sm font-medium">Username</label>
              <input
                className="mt-2 w-full rounded-lg border border-border bg-background px-3 py-2"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                autoComplete="username"
                required
              />
            </div>
            <div>
              <label className="text-sm font-medium">Password</label>
              <input
                className="mt-2 w-full rounded-lg border border-border bg-background px-3 py-2"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete="current-password"
                required
              />
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
            <button
              type="submit"
              className="w-full rounded-lg bg-primary py-2 text-center font-medium text-primary-foreground hover:opacity-90"
              disabled={loading}
            >
              {loading ? "Authenticating..." : "Access Dashboard"}
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-muted/40 px-4 py-10">
      <div className="mx-auto flex max-w-6xl flex-col gap-6">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm uppercase tracking-wide text-muted-foreground">NESCO Admin</p>
            <h1 className="text-3xl font-semibold">Operations Dashboard</h1>
            <p className="text-sm text-muted-foreground">
              Live view of bot adoption, meters, and recent customer activity.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              className="rounded-lg border border-border px-4 py-2 text-sm font-medium hover:bg-background"
              onClick={() => fetchStats()}
              disabled={loading}
            >
              {loading ? "Refreshing..." : "Refresh"}
            </button>
            <button
              className="rounded-lg bg-destructive px-4 py-2 text-sm font-medium text-destructive-foreground hover:opacity-90"
              onClick={handleLogout}
            >
              Logout
            </button>
          </div>
        </div>

        <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
          <StatCard title="Total Users" value={stats.total_users} subtitle="Unique Telegram accounts" />
          <StatCard title="Total Meters" value={stats.total_meters} subtitle="Registered prepaid meters" />
          <StatCard title="Reminders Enabled" value={stats.reminders_enabled} subtitle="Daily reminder opt-ins" />
          <StatCard title="Active (24h)" value={stats.active_users_24h} subtitle="Users with recent readings" />
        </div>

        <div className="grid gap-6 md:grid-cols-2">
          <SectionCard title="Newest Users">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs uppercase tracking-wide text-muted-foreground">
                    <th className="py-2">User</th>
                    <th className="py-2">Telegram ID</th>
                    <th className="py-2">Joined</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.latest_users.map((user) => (
                    <tr key={user.id} className="border-t border-border">
                      <td className="py-2 font-medium">{user.username ?? `User ${user.telegram_user_id}`}</td>
                      <td className="py-2 text-muted-foreground">{user.telegram_user_id}</td>
                      <td className="py-2 text-muted-foreground">{formatDate(user.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </SectionCard>

          <SectionCard title="Latest Meters">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs uppercase tracking-wide text-muted-foreground">
                    <th className="py-2">Meter</th>
                    <th className="py-2">Owner</th>
                    <th className="py-2">Added</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.latest_meters.map((meter) => (
                    <tr key={meter.id} className="border-t border-border">
                      <td className="py-2 font-medium">
                        {meter.name}
                        <span className="block text-xs text-muted-foreground">#{meter.number}</span>
                      </td>
                      <td className="py-2 text-muted-foreground">{meter.owner}</td>
                      <td className="py-2 text-muted-foreground">{formatDate(meter.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </SectionCard>
        </div>

        <SectionCard title="Recent Balance Activity">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase tracking-wide text-muted-foreground">
                  <th className="py-2">Meter</th>
                  <th className="py-2">User</th>
                  <th className="py-2">Balance</th>
                  <th className="py-2">Recorded</th>
                </tr>
              </thead>
              <tbody>
                {stats.recent_activity.map((entry) => (
                  <tr key={entry.id} className="border-t border-border">
                    <td className="py-2 font-medium">
                      {entry.meter_name}
                      <span className="block text-xs text-muted-foreground">#{entry.meter_number}</span>
                    </td>
                    <td className="py-2 text-muted-foreground">{entry.user}</td>
                    <td className="py-2 font-semibold text-foreground">{entry.balance.toFixed(2)} BDT</td>
                    <td className="py-2 text-muted-foreground">{formatDate(entry.recorded_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionCard>
      </div>
    </div>
  );
};

export default AdminDashboard;
