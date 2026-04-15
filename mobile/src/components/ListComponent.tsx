import React from "react";
import { View, StyleSheet } from "react-native";
import { Text } from "react-native-paper";
import { MaterialIcons } from "@expo/vector-icons";
import { Event } from "../models/event";
import { formatDuration, formatLocation } from "../common/formatting";
import { formatDateWithWeekday } from "../utils/datetime/dateUtils";
import { Colors, Radius, Shadow } from "../theme";

interface ListComponentProps {
  events: Event[];
}

export default function ListComponent({ events }: ListComponentProps) {
  if (!events || events.length === 0) return null;

  return (
    <View style={styles.container}>
      {events.map((event, index) => (
        <View key={event.id} style={[styles.card, index > 0 && styles.cardMargin]}>
          <View style={styles.accent} />
          <View style={styles.body}>
            <View style={styles.titleRow}>
              <Text style={styles.title} numberOfLines={2}>
                {event.title}
              </Text>
              {event.recurrence_type && (
                <MaterialIcons name="repeat" size={14} color={Colors.primary} style={styles.repeatIcon} />
              )}
            </View>
            <View style={styles.details}>
              <View style={styles.detailRow}>
                <MaterialIcons name="schedule" size={13} color={Colors.primary} />
                <Text style={styles.detailText}>{formatDateWithWeekday(event.startDate)}</Text>
              </View>
              <View style={styles.detailRow}>
                <MaterialIcons name="timer" size={13} color={Colors.textTertiary} />
                <Text style={styles.detailText}>{formatDuration(event.duration)}</Text>
              </View>
              <View style={styles.detailRow}>
                <MaterialIcons name="location-on" size={13} color={Colors.textTertiary} />
                <Text style={styles.detailText} numberOfLines={1}>
                  {formatLocation(event.location)}
                </Text>
              </View>
            </View>
          </View>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: 8,
    marginTop: 4,
  },
  card: {
    backgroundColor: Colors.surface,
    borderRadius: Radius.lg,
    borderWidth: 1,
    borderColor: Colors.border,
    flexDirection: "row",
    overflow: "hidden",
    ...Shadow.sm,
  },
  cardMargin: {
    marginTop: 0,
  },
  accent: {
    width: 4,
    backgroundColor: Colors.primary,
  },
  body: {
    flex: 1,
    padding: 12,
  },
  titleRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    marginBottom: 8,
    gap: 6,
  },
  title: {
    flex: 1,
    fontSize: 15,
    fontWeight: "600",
    color: Colors.textPrimary,
    lineHeight: 20,
  },
  repeatIcon: {
    marginTop: 2,
  },
  details: {
    gap: 5,
  },
  detailRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  detailText: {
    fontSize: 13,
    color: Colors.textSecondary,
    flex: 1,
  },
});
