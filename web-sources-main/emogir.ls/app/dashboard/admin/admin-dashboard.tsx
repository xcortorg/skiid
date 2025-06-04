"use client";

import { DataTable } from "@/components/ui/data-table";
import { toast } from "sonner";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Input } from "@/components/ui/input";
import { useReactTable, getCoreRowModel, getPaginationRowModel, getSortedRowModel, getFilteredRowModel } from "@tanstack/react-table";

const formatDate = (date: string | Date) => {
  return new Date(date).toISOString().split("T")[0];
};

const badges = [
  { id: "OWNER", label: "Owner", icon: "/badges/owner.svg" },
  { id: "CO_OWNER", label: "Co-Owner", icon: "/badges/co-owner.svg" },
  { id: "OG", label: "OG", icon: "/badges/og.svg" },
  { id: "PREMIUM", label: "Premium", icon: "/badges/premium.svg" },
  { id: "STAFF", label: "Staff", icon: "/badges/staff.svg" },
  { id: "VERIFIED", label: "Verified", icon: "/badges/verified.svg" },
];

export function AdminDashboard() {
  const [users, setUsers] = useState([]);
  const [inviteCodes, setInviteCodes] = useState([]);
  const [loading, setLoading] = useState(true);

  const table = useReactTable({
    data: inviteCodes,
    columns: [
      {
        accessorKey: "code",
        header: "Code",
      },
      {
        accessorFn: (row: any) => row.createdBy?.slug || "Unknown",
        header: "Created By",
      },
      {
        accessorKey: "createdAt",
        header: "Created At",
        cell: ({ row }: { row: any }) => formatDate(row.getValue("createdAt")),
      },
      {
        accessorFn: (row: any) => row.usedBy?.slug || "Unused",
        header: "Used By",
        cell: ({ row }: { row: any }) => {
          const slug = row.original.usedBy?.slug;
          return slug ? (
            <Link
              href={`/dashboard/admin/user/${row.original.usedBy.id}`}
              className="text-primary hover:underline"
            >
              {slug}
            </Link>
          ) : (
            "Unused"
          );
        },
      },
      {
        accessorKey: "usedAt",
        header: "Used At",
        cell: ({ row }: { row: any }) =>
          row.getValue("usedAt")
            ? formatDate(row.getValue("usedAt"))
            : "Not used",
      },
      {
        id: "actions",
        header: "Actions",
        cell: ({ row }: { row: any }) => (
          <div className="flex items-center justify-end space-x-2">
            <button
              onClick={async () => {
                try {
                  await fetch(`/api/admin/invites/${row.original.id}`, {
                    method: "DELETE",
                  });
                  toast.success("Invite code deleted");
                  window.location.reload();
                } catch (error) {
                  toast.error("Failed to delete invite code");
                }
              }}
              className="px-4 py-2 bg-red-500/10 text-red-500 hover:bg-red-500/20 rounded-lg transition-colors"
            >
              Delete
            </button>
          </div>
        ),
      },
    ],
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  });

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [usersResponse, invitesResponse] = await Promise.all([
          fetch("/api/admin/users"),
          fetch("/api/admin/invites"),
        ]);

        if (!usersResponse.ok || !invitesResponse.ok) {
          throw new Error("Failed to fetch data");
        }

        const usersData = await usersResponse.json();
        const invitesData = await invitesResponse.json();

        setUsers(usersData);
        setInviteCodes(invitesData);
      } catch (error) {
        toast.error("Failed to load admin data");
        console.error(error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const userColumns = [
    {
      header: "Username",
      accessorKey: "username",
      cell: ({ row }: { row: any }) => (
        <Link
          href={`/dashboard/admin/user/${row.original.id}`}
          className="text-primary hover:underline"
        >
          {row.getValue("username")}
        </Link>
      ),
    },
    {
      header: "Email",
      accessorKey: "email",
    },
    {
      header: "Created At",
      accessorKey: "createdAt",
      cell: ({ row }: { row: any }) => formatDate(row.getValue("createdAt")),
    },
    {
      header: "2FA",
      accessorKey: "twoFactorEnabled",
      cell: ({ row }: { row: any }) => (
        <span
          className={`px-2 py-1 rounded-full text-xs ${
            row.getValue("twoFactorEnabled")
              ? "bg-green-500/10 text-green-500"
              : "bg-white/10 text-white/60"
          }`}
        >
          {row.getValue("twoFactorEnabled") ? "Enabled" : "Disabled"}
        </span>
      ),
    },
    {
      header: "Links",
      accessorKey: "_count.links",
    },
    {
      header: "Sessions",
      accessorKey: "_count.sessions",
    },
    {
      header: "Status",
      accessorKey: "isDisabled",
      cell: ({ row }: { row: any }) => (
        <span
          className={`px-2 py-1 rounded-full text-xs ${
            row.getValue("isDisabled")
              ? "bg-red-500/10 text-red-500"
              : "bg-green-500/10 text-green-500"
          }`}
        >
          {row.getValue("isDisabled") ? "Disabled" : "Active"}
        </span>
      ),
    },
    {
      header: "Actions",
      cell: ({ row }: { row: any }) => (
        <Link
          href={`/dashboard/admin/user/${row.original.id}`}
          className="px-4 py-2 bg-primary/10 text-primary hover:bg-primary/20 rounded-lg transition-colors"
        >
          Manage
        </Link>
      ),
    },
  ];

  const inviteColumns = [
    {
      header: "Code",
      accessorKey: "code",
    },
    {
      header: "Created By",
      accessorFn: (row: any) => row.createdBy?.slug || "Unknown",
    },
    {
      header: "Created At",
      accessorKey: "createdAt",
      cell: ({ row }: { row: any }) => formatDate(row.getValue("createdAt")),
    },
    {
      header: "Used By",
      accessorFn: (row: any) => row.usedBy?.slug || "Unused",
      cell: ({ row }: { row: any }) => {
        const slug = row.original.usedBy?.slug;
        return slug ? (
          <Link
            href={`/dashboard/admin/user/${row.original.usedBy.id}`}
            className="text-primary hover:underline"
          >
            {slug}
          </Link>
        ) : (
          "Unused"
        );
      },
    },
    {
      header: "Used At",
      accessorKey: "usedAt",
      cell: ({ row }: { row: any }) =>
        row.getValue("usedAt")
          ? formatDate(row.getValue("usedAt"))
          : "Not used",
    },
    {
      header: "Actions",
      cell: ({ row }: { row: any }) => (
        <button
          onClick={async () => {
            try {
              await fetch(`/api/admin/invites/${row.original.id}`, {
                method: "DELETE",
              });
              toast.success("Invite code deleted");
              window.location.reload();
            } catch (error) {
              toast.error("Failed to delete invite code");
            }
          }}
          className="px-4 py-2 bg-red-500/10 text-red-500 hover:bg-red-500/20 rounded-lg transition-colors"
        >
          Delete
        </button>
      ),
    },
  ];

  return (
    <div className="min-h-screen bg-black/40">
      <div className="p-8 space-y-8">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold">Admin Dashboard</h2>
            <p className="text-white/60 mt-1">
              Manage users, invites, and system settings
            </p>
          </div>
          <div className="flex items-center gap-4">
            <div className="bg-black/20 rounded-lg px-6 py-3">
              <p className="text-sm text-white/60">Total Users</p>
              <p className="text-2xl font-bold text-primary">{users.length}</p>
            </div>
            <div className="bg-black/20 rounded-lg px-6 py-3">
              <p className="text-sm text-white/60">Active Invites</p>
              <p className="text-2xl font-bold text-primary">
                {inviteCodes.filter((code: any) => !code.usedAt).length}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-black/20 border border-white/5 rounded-xl">
          <div className="p-6 border-b border-white/5">
            <div className="flex items-center justify-between">
              <h3 className="text-xl font-semibold">Invite Codes</h3>
              <button
                onClick={async () => {
                  try {
                    const response = await fetch("/api/admin/invites", {
                      method: "POST",
                    });
                    if (!response.ok) throw new Error();
                    toast.success("Invite code created");
                    window.location.reload();
                  } catch {
                    toast.error("Failed to create invite code");
                  }
                }}
                className="px-4 py-2 bg-primary/10 text-primary hover:bg-primary/20 rounded-lg transition-colors"
              >
                Generate New Code
              </button>
            </div>
          </div>
          <div className="p-6">
            {/* <Input
              placeholder="Filter codes..."
              value={(table.getColumn("code")?.getFilterValue() as string) ?? ""}
              onChange={(event) =>
                table.getColumn("code")?.setFilterValue(event.target.value)
              }
              className="max-w-sm mb-4 bg-black/40"
            /> */}
            <DataTable columns={inviteColumns} data={inviteCodes} />
          </div>
        </div>

        <div className="bg-black/20 border border-white/5 rounded-xl">
          <div className="p-6 border-b border-white/5">
            <div className="flex items-center justify-between">
              <h3 className="text-xl font-semibold">Users</h3>
              <Input
                placeholder="Filter users..."
                value={(table.getColumn("username")?.getFilterValue() as string) ?? ""}
                onChange={(event) =>
                  table.getColumn("username")?.setFilterValue(event.target.value)
                }
                className="w-64 bg-black/40"
              />
            </div>
          </div>
          <div className="p-6">
            <DataTable columns={userColumns} data={users} />
          </div>
        </div>
      </div>
    </div>
  );
}
