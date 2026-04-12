import AsyncStorage from "@react-native-async-storage/async-storage";
import * as ExpoLinking from "expo-linking";

const KEY = "@calendarai_pending_route";

export type PendingNav =
  | { screen: "Calendar"; params?: { eventId?: string } }
  | { screen: "Profile" };

function parseEventIdFromUrl(url: string): string | undefined {
  const parsed = ExpoLinking.parse(url);
  const qp = parsed.queryParams as Record<string, string> | undefined;
  const fromQuery = qp?.eventId;
  if (fromQuery) return fromQuery;

  const normalized = (parsed.path || "")
    .replace(/^\//, "")
    .replace(/^--\//, "");
  const parts = normalized.split("/").filter(Boolean);
  if (parts[0] === "calendar" && parts[1]) {
    try {
      return decodeURIComponent(parts[1]);
    } catch {
      return parts[1];
    }
  }
  return undefined;
}

/** Save target screen (and optional event) when user opens a link before logging in. */
export async function savePendingRouteFromUrl(url: string): Promise<void> {
  const { path } = ExpoLinking.parse(url);
  const normalized = (path || "").replace(/^\//, "").replace(/^--\//, "");
  const segment = normalized.split("/")[0] || "";
  const eventId = parseEventIdFromUrl(url);

  if (segment === "calendar") {
    const payload: PendingNav = {
      screen: "Calendar",
      ...(eventId ? { params: { eventId } } : {}),
    };
    await AsyncStorage.setItem(KEY, JSON.stringify(payload));
  } else if (segment === "profile") {
    await AsyncStorage.setItem(KEY, JSON.stringify({ screen: "Profile" }));
  }
}

export async function consumePendingRoute(): Promise<PendingNav | null> {
  const raw = await AsyncStorage.getItem(KEY);
  if (raw) await AsyncStorage.removeItem(KEY);
  if (!raw) return null;

  try {
    const v = JSON.parse(raw) as unknown;
    if (v && typeof v === "object" && "screen" in v) {
      const o = v as { screen: string; params?: { eventId?: string } };
      if (o.screen === "Calendar") {
        return { screen: "Calendar", params: o.params };
      }
      if (o.screen === "Profile") {
        return { screen: "Profile" };
      }
    }
  } catch {
    // legacy plain string
  }

  if (raw === "Calendar" || raw === "Profile") {
    return { screen: raw };
  }
  return null;
}
