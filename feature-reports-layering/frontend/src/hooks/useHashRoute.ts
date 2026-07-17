import { useEffect, useState } from "react";

export type Route =
  | { view: "browse" }
  | { view: "dashboard" }
  | { view: "report"; slug: string }
  | { view: "upload" }
  | { view: "edit"; slug: string };

// Slug-navigable hash routes: #/  #/dashboard  #/r/<slug>  #/upload  #/edit/<slug>
export function parseHash(hash: string): Route {
  const clean = hash.replace(/^#\/?/, "");
  if (clean === "dashboard") return { view: "dashboard" };
  if (clean === "upload") return { view: "upload" };
  const edit = clean.match(/^edit\/(.+)$/);
  if (edit) return { view: "edit", slug: decodeURIComponent(edit[1]) };
  const m = clean.match(/^r\/(.+)$/);
  if (m) return { view: "report", slug: decodeURIComponent(m[1]) };
  return { view: "browse" };
}

export function routeToHash(route: Route): string {
  switch (route.view) {
    case "report":
      return `#/r/${encodeURIComponent(route.slug)}`;
    case "edit":
      return `#/edit/${encodeURIComponent(route.slug)}`;
    case "upload":
      return "#/upload";
    case "dashboard":
      return "#/dashboard";
    default:
      return "#/";
  }
}

export function navigate(route: Route): void {
  window.location.hash = routeToHash(route);
}

export function useHashRoute(): Route {
  const [route, setRoute] = useState<Route>(() =>
    parseHash(window.location.hash),
  );
  useEffect(() => {
    const onChange = () => setRoute(parseHash(window.location.hash));
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return route;
}
