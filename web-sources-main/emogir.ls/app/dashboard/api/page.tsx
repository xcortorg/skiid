"use client";

import { DataCard } from "@/components/ui/data-card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  IconKey,
  IconTrash,
  IconCopy,
  IconChartBar,
} from "@tabler/icons-react";
import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useRouter } from "next/navigation";
import { useToast } from "@/components/ui/toast-provider";

interface ApiToken {
  id: string;
  name: string;
  token?: string;
  lastUsed?: Date;
  createdAt: Date;
  expiresAt: Date;
  rateLimit: number;
}

export default function ApiDashboard() {
  const router = useRouter();
  const { toast } = useToast();
  const [tokens, setTokens] = useState<ApiToken[]>([]);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [newTokenName, setNewTokenName] = useState("");
  const [loading, setLoading] = useState(true);
  const [apiEnabled, setApiEnabled] = useState(false);
  const [maxKeys, setMaxKeys] = useState(0);
  const [newToken, setNewToken] = useState<string | null>(null);

  useEffect(() => {
    fetchTokens();
  }, []);

  const fetchTokens = async () => {
    try {
      const response = await fetch("/api/v1/auth/token");
      const data = await response.json();
      setTokens(data.tokens);
      setApiEnabled(data.apiEnabled);
      setMaxKeys(data.maxKeys);
      setLoading(false);
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to load API tokens",
        variant: "error",
      });
      setLoading(false);
    }
  };

  const createToken = async () => {
    try {
      const response = await fetch("/api/v1/auth/token", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newTokenName }),
      });

      if (!response.ok) throw new Error();

      const data = await response.json();
      setTokens([...tokens, data]);
      setShowCreateDialog(false);
      setNewTokenName("");
      setNewToken(data.token);
      toast({
        title: "Success",
        description: "API token created successfully",
        variant: "success",
      });
    } catch {
      toast({
        title: "Error",
        description: "Failed to create API token",
        variant: "error",
      });
    }
  };

  const revokeToken = async (id: string) => {
    try {
      const response = await fetch(`/api/v1/auth/token/${id}`, {
        method: "DELETE",
      });
      if (!response.ok) throw new Error();

      setTokens(tokens.filter((token) => token.id !== id));
      toast({
        title: "Success",
        description: "API token revoked successfully",
        variant: "success",
      });
    } catch {
      toast({
        title: "Error",
        description: "Failed to revoke API token",
        variant: "error",
      });
    }
  };

  if (!apiEnabled) {
    return (
      <div className="min-h-screen bg-black/40 p-8">
        <div className="max-w-4xl">
          <div className="bg-black/20 border border-white/5 rounded-xl p-6 text-center">
            <h2 className="text-xl font-semibold mb-2">
              API Access Not Enabled
            </h2>
            <p className="text-white/60 mb-4">
              Contact support to enable API access for your account.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black/40 p-8">
      <div className="mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold">API Management</h1>
            <p className="text-white/60">Manage your API tokens</p>
          </div>
          <div className="flex gap-2">
            <Button
              onClick={() => router.push("/dashboard/api/analytics")}
              className="flex items-center gap-2"
            >
              <IconChartBar size={16} />
              View Analytics
            </Button>
            <Button
              onClick={() => setShowCreateDialog(true)}
              disabled={tokens.length >= maxKeys}
              className="flex items-center gap-2"
            >
              <IconKey size={16} />
              Create Token
            </Button>
          </div>
        </div>

        <DataCard title="API Tokens" icon={IconKey}>
          {tokens.length === 0 ? (
            <div className="text-center py-8 text-white/60">
              No API tokens created yet
            </div>
          ) : (
            <div className="space-y-4">
              {tokens.map((token) => (
                <div
                  key={token.id}
                  className="flex items-center justify-between p-4 bg-black/20 rounded-lg"
                >
                  <div className="space-y-1">
                    <p className="font-medium">{token.name}</p>
                    <p className="text-sm text-white/60">
                      Created {new Date(token.createdAt).toLocaleDateString()}
                      {token.lastUsed &&
                        ` • Last used ${new Date(
                          token.lastUsed,
                        ).toLocaleDateString()}`}
                    </p>
                  </div>
                  <Button
                    onClick={() => revokeToken(token.id)}
                    className="bg-red-500/10 border-red-500/20 text-red-500"
                  >
                    <IconTrash size={16} />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </DataCard>
      </div>

      {newToken && (
        <Dialog open={!!newToken} onOpenChange={() => setNewToken(null)}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Save Your API Token</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <p className="text-white/60 text-sm">
                Copy your API token now. You won&apos;t be able to see it again!
              </p>
              <div className="bg-black/20 p-4 rounded-lg break-all font-mono text-sm">
                {newToken}
              </div>
              <div className="flex justify-end gap-2">
                <Button
                  onClick={() => {
                    navigator.clipboard.writeText(newToken);
                    toast({
                      title: "Copied",
                      description: "API key copied to clipboard",
                      variant: "success",
                    });
                  }}
                  className="bg-white/5"
                >
                  <IconCopy size={16} className="mr-2" />
                  Copy
                </Button>
                <Button
                  onClick={() => setNewToken(null)}
                  className="bg-primary"
                >
                  Done
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      )}

      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create API Token</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="text-sm text-white/60">Token Name</label>
              <Input
                value={newTokenName}
                onChange={(e) => setNewTokenName(e.target.value)}
                placeholder="e.g., Development Token"
              />
            </div>
            <div className="flex justify-end gap-2">
              <Button
                onClick={() => setShowCreateDialog(false)}
                className="bg-white/5"
              >
                Cancel
              </Button>
              <Button
                onClick={createToken}
                disabled={!newTokenName}
                className="bg-primary"
              >
                Create Token
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
