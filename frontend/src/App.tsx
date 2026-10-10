import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { getHealth } from "@/lib/api";

type ConnectionState = "checking" | "online" | "offline";

function App() {
  const [state, setState] = useState<ConnectionState>("checking");
  const [useMock, setUseMock] = useState<boolean | null>(null);

  const checkHealth = async () => {
    setState("checking");
    try {
      const health = await getHealth();
      setUseMock(health.use_mock);
      setState("online");
    } catch {
      setUseMock(null);
      setState("offline");
    }
  };

  useEffect(() => {
    void checkHealth();
  }, []);

  return (
    <main className="min-h-svh bg-background text-foreground">
      <div className="mx-auto flex min-h-svh max-w-2xl flex-col items-center justify-center gap-6 px-6 text-center">
        <div className="space-y-2">
          <h1 className="text-4xl font-bold tracking-tight text-primary">
            KaagazMitra
          </h1>
          <p className="text-lg text-muted-foreground">
            Your document &amp; application-readiness assistant
          </p>
        </div>

        {state === "checking" && (
          <p className="text-base text-muted-foreground" role="status">
            Checking backend connection…
          </p>
        )}

        {state === "online" && (
          <div
            className="rounded-lg border border-border bg-card px-6 py-4 text-xl font-semibold text-primary shadow-sm"
            role="status"
          >
            Backend connected ✅
            {useMock && (
              <span className="ml-2 text-sm font-normal text-muted-foreground">
                (mock mode)
              </span>
            )}
          </div>
        )}

        {state === "offline" && (
          <div
            className="rounded-lg border border-destructive bg-card px-6 py-4 text-xl font-semibold text-destructive shadow-sm"
            role="status"
          >
            Backend offline
          </div>
        )}

        <Button variant="outline" onClick={checkHealth}>
          Re-check connection
        </Button>
      </div>
    </main>
  );
}

export default App;
