import type { LinkingOptions } from "@react-navigation/native";
import * as Linking from "expo-linking";

import type { RootStackParamList } from "./types";

/**
 * Deep linking:
 * - calendarai://calendar → Calendar
 * - calendarai://calendar?eventId=<id> → Calendar + open that event (use encodeURIComponent for id)
 * - calendarai://calendar/<id> → same
 * - calendarai://profile → Profile
 *
 * Universal Links (https://yourdomain.com/...) require apple-app-site-association
 * on your domain — add the same path config and associatedDomains in app.json when ready.
 */
/** RN's LinkingOptions typing doesn't model multiple path patterns per screen; runtime supports it. */
export const linking = {
  prefixes: [
    Linking.createURL("/"),
    "calendarai://",
  ],
  config: {
    screens: {
      Home: "",
      Calendar: [
        {
          path: "calendar/:eventId",
          parse: {
            eventId: (eventId: string) => eventId,
          },
        },
        {
          path: "calendar",
          parse: {
            eventId: (eventId?: string) => eventId ?? undefined,
          },
        },
      ],
      Profile: "profile",
    },
  },
} as LinkingOptions<RootStackParamList>;
