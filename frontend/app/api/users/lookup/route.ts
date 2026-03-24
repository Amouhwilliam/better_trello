import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

const API_URL = process.env.API_URL ?? "http://api:8000";

export async function GET(req: NextRequest) {
  const email = req.nextUrl.searchParams.get("email");
  if (!email) return NextResponse.json({ error: "email required" }, { status: 400 });

  const token = (await cookies()).get("bt_token")?.value;

  let res: Response;
  try {
    res = await fetch(`${API_URL}/users`, {
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });
  } catch {
    return NextResponse.json({ error: "Service unavailable. Please try again later." }, { status: 503 });
  }

  if (!res.ok) return NextResponse.json({ error: "upstream error" }, { status: 502 });

  const users: { id: string; email: string; fullname: string }[] = await res.json();
  const user = users.find((u) => u.email.toLowerCase() === email.toLowerCase());

  if (!user) return NextResponse.json({ exists: false }, { status: 404 });
  return NextResponse.json({ exists: true, user });
}
