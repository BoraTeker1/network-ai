import { redirect } from "next/navigation";

// The dashboard is the app's command center. Route the homepage there so the
// first thing a user sees is "Today's Networking Mission". /pitch stays separate.
export default function Home() {
  redirect("/dashboard");
}
