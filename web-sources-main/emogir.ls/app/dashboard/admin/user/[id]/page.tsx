import { UserManagement } from "./user-management";

export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const resolvedParams = await params;
  return <UserManagement id={resolvedParams.id} />;
}
