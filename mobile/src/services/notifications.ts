import * as Notifications from "expo-notifications";
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
    const tokenData = await Notifications.getExpoPushTokenAsync({
      projectId: "calendar-ai", // matches app.json slug
    });
    await calendarAPI.updatePushToken(tokenData.data);
    console.log("Push token registered:", tokenData.data);
  } catch (error) {
    console.error("Failed to get/register push token:", error);
  }
}
