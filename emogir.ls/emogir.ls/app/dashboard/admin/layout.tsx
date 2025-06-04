import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { redirect } from "next/navigation";
import { Session } from "next-auth";

const ADMIN_IDS = ["cm8a3itl40000vdtw948gpfp1", "cm8afkf1n000dpa7h6qhtr50v"];

export default async function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = (await getServerSession(
    authOptions as any,
  )) as Session | null;

  if (!session?.user?.id || !ADMIN_IDS.includes(session.user.id)) {
    redirect("/dashboard");
  }

  return <>{children}</>;
}
