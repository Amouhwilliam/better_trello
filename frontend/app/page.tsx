import { redirect } from "next/navigation";
import { cookies } from "next/headers";
import LoginClient from "./LoginClient";

export default async function HomePage() {
  const token = (await cookies()).get("bt_token")?.value;
  if (token) redirect("/dashboard");

  return <LoginClient />;
}
