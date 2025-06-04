import { db } from "@/lib/db";

export async function isAccountRestricted(userId: string) {
  const user = await db.user.findUnique({
    where: { id: userId },
    select: { accountStatus: true, isDisabled: true },
  });

  return !user || user.accountStatus !== "ACTIVE" || user.isDisabled;
}
