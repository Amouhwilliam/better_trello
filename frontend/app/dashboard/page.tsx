import { redirect } from "next/navigation";
import { cookies } from "next/headers";
import { DashboardClient } from "./DashboardClient";

export default async function DashboardPage() {
  const token = (await cookies()).get("bt_token")?.value;
  if (!token) redirect("/");

  return <DashboardClient />;
}
