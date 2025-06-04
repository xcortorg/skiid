"use client";

import { ColumnDef } from "@tanstack/react-table";
import { Badge } from "@/components/ui/badge";
import { formatDistanceToNow } from "date-fns";
import { Button } from "./button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "./dialog";
import { IconEye } from "@tabler/icons-react";
import { useState } from "react";
import { useToast } from "@/components/ui/toast-provider";

export type User = {
  id: string;
  email: string;
  username: string;
  createdAt: Date;
  twoFactorEnabled: boolean;
  isPremium: boolean;
  _count: {
    sessions: number;
    links: number;
  };
};

const UserDetails = ({ user }: { user: User }) => {
  const { toast } = useToast();
  const [isLoading, setIsLoading] = useState(false);

  const handleDisableAccount = async () => {
    if (!confirm("Are you sure you want to disable this account?")) return;

    setIsLoading(true);
    try {
      const res = await fetch(`/api/admin/users/${user.id}/disable`, {
        method: "POST",
      });

      if (!res.ok) throw new Error("Failed to disable account");

      toast({
        title: "Account disabled",
        description: "Account disabled successfully",
        variant: "success",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to disable account",
        variant: "error",
      });
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  const handlePremiumToggle = async () => {
    setIsLoading(true);
    try {
      const res = await fetch(`/api/admin/users/${user.id}/premium`, {
        method: "POST",
        body: JSON.stringify({
          until: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000),
        }),
      });

      if (!res.ok) throw new Error("Failed to update premium status");
      toast({
        title: "Premium updated",
        description: "Premium status updated successfully",
        variant: "success",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to update premium status",
        variant: "error",
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <h4 className="text-sm text-zinc-400">Username</h4>
          <p>{user.username}</p>
        </div>
        <div>
          <h4 className="text-sm text-zinc-400">Email</h4>
          <p>{user.email}</p>
        </div>
        <div>
          <h4 className="text-sm text-zinc-400">Joined</h4>
          <p>{formatDistanceToNow(user.createdAt, { addSuffix: true })}</p>
        </div>
        <div>
          <h4 className="text-sm text-zinc-400">2FA Status</h4>
          <Badge variant={user.twoFactorEnabled ? "default" : "secondary"}>
            {user.twoFactorEnabled ? "Enabled" : "Disabled"}
          </Badge>
        </div>
      </div>

      <div className="space-y-2">
        <h4 className="text-sm text-zinc-400">Activity</h4>
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-black/20 p-4 rounded-lg">
            <p className="text-2xl font-bold">{user._count.sessions}</p>
            <p className="text-sm text-zinc-400">Active Sessions</p>
          </div>
          <div className="bg-black/20 p-4 rounded-lg">
            <p className="text-2xl font-bold">{user._count.links}</p>
            <p className="text-sm text-zinc-400">Links</p>
          </div>
        </div>
      </div>

      <div className="space-y-2">
        <Button
          className="w-full bg-black/20 hover:bg-black/40"
          onClick={handlePremiumToggle}
          disabled={isLoading}
        >
          {user.isPremium ? "Remove Premium" : "Grant Premium"}
        </Button>
        <Button
          className="w-full bg-red-500 hover:bg-red-600"
          onClick={handleDisableAccount}
          disabled={isLoading}
        >
          {isLoading ? "Disabling..." : "Disable Account"}
        </Button>
      </div>
    </div>
  );
};

const DateCell = ({ date }: { date: Date }) => (
  <span>{formatDistanceToNow(date, { addSuffix: true })}</span>
);

const TwoFactorCell = ({ enabled }: { enabled: boolean }) => (
  <Badge variant={enabled ? "default" : "secondary"}>
    {enabled ? "Enabled" : "Disabled"}
  </Badge>
);

export const columns: ColumnDef<User>[] = [
  {
    accessorKey: "username",
    header: "Username",
  },
  {
    accessorKey: "email",
    header: "Email",
  },
  {
    accessorKey: "createdAt",
    header: "Joined",
    cell: ({ row }) => <DateCell date={row.original.createdAt} />,
  },
  {
    accessorKey: "twoFactorEnabled",
    header: "2FA",
    cell: ({ row }) => (
      <TwoFactorCell enabled={row.original.twoFactorEnabled} />
    ),
  },
  {
    accessorKey: "_count.sessions",
    header: "Sessions",
  },
  {
    accessorKey: "_count.links",
    header: "Links",
  },
  {
    id: "actions",
    cell: ({ row }) => (
      <Dialog>
        <DialogTrigger asChild>
          <Button className="bg-black/20 hover:bg-black/40">
            <IconEye className="h-4 w-4" />
          </Button>
        </DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>User Details</DialogTitle>
          </DialogHeader>
          <UserDetails user={row.original} />
        </DialogContent>
      </Dialog>
    ),
  },
];
