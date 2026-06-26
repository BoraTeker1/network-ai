import { redirect } from "next/navigation";

// Turkey → remote/EU focus: the default journey starts at the opportunity feed,
// which flows into the outreach copilot. /pitch and the legacy /dashboard remain
// reachable directly.
export default function Home() {
  redirect("/opportunities");
}
