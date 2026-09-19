import { Href, Redirect } from "expo-router";

export default function AccountRedirect() {
  return <Redirect href={"/settings" as Href} />;
}
