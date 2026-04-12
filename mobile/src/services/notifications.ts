import * as Notifications from "expo-notifications";
import Constants from "expo-constants";
import { Platform } from "react-native";
import { calendarAPI } from "./api";

// Show alerts and play sounds while the app is in the foreground
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
    shouldShowBanner: true,
    shouldShowList: true,
  }),
});

export async function registerForPushNotifications(): Promise<void> {
  // Physical device check is skipped — Expo handles it gracefully on simulators
  const { status: existingStatus } = await Notifications.getPermissionsAsync();
  let finalStatus = existingStatus;

  if (existingStatus !== "granted") {
    const { status } = await Notifications.requestPermissionsAsync();
    finalStatus = status;
  }

  if (finalStatus !== "granted") {
    console.log("Push notification permission not granted");
    return;
  }

  // Android requires a notification channel
  if (Platform.OS === "android") {
    await Notifications.setNotificationChannelAsync("default", {
      name: "Calendar Reminders",
      importance: Notifications.AndroidImportance.HIGH,
      vibrationPattern: [0, 250, 250, 250],
      lightColor: "#6366F1",
    });
  }

  try {
    // Prefer the EAS project UUID (extra.eas.projectId in app.json) which is required
    // for standalone/EAS builds. Falls back to the slug for local Expo Go development.
    const projectId =
      Constants.expoConfig?.extra?.eas?.projectId ??
      Constants.easConfig?.projectId ??
      Constants.expoConfig?.slug;
    const tokenData = await Notifications.getExpoPushTokenAsync({ projectId });
    await calendarAPI.updatePushToken(tokenData.data);
    console.log("Push token registered:", tokenData.data);
  } catch (error) {
    console.error("Failed to get/register push token:", error);
  }
}
