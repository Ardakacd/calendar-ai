import React from "react";
import { View, StyleSheet } from "react-native";
import { Text } from "react-native-paper";
import { MaterialIcons } from "@expo/vector-icons";
import { Colors, Radius } from "../theme";

export interface ConflictSuggestion {
  startDate: string;
  endDate: string;
  reason?: string;
}

interface ConflictComponentProps {
  conflictMessage: string;
  suggestions: ConflictSuggestion[];
}

function formatDateTime(iso: string): { date: string; time: string } {
  try {
    const dt = new Date(iso);
    const date = dt.toLocaleDateString("en-US", {
      weekday: "short",
      month: "short",
      day: "numeric",
    });
    const time = dt.toLocaleTimeString("en-US", {
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    });
    return { date, time };
  } catch {
    return { date: "", time: iso };
  }
}

export default function ConflictComponent({ conflictMessage, suggestions }: ConflictComponentProps) {
  const headline = conflictMessage.split("\n")[0];

  return (
    <View style={styles.container}>
      <View style={styles.warningRow}>
        <View style={styles.warningIcon}>
          <MaterialIcons name="warning-amber" size={16} color={Colors.warning} />
        </View>
        <Text style={styles.warningText}>{headline}</Text>
      </View>

      {suggestions.length > 0 && (
        <>
          <Text style={styles.altLabel}>Available times</Text>
          {suggestions.map((s, i) => {
            const start = formatDateTime(s.startDate);
            const end = formatDateTime(s.endDate);
            const sameDay = start.date === end.date;
            return (
              <View key={i} style={styles.slotCard}>
                <MaterialIcons name="schedule" size={15} color={Colors.primary} />
                <View style={styles.slotText}>
                  <Text style={styles.slotTime}>
                    {start.time} – {end.time}
                  </Text>
                  <Text style={styles.slotDate}>
                    {sameDay ? start.date : `${start.date} – ${end.date}`}
                  </Text>
                </View>
              </View>
            );
          })}
        </>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: 10,
  },
  warningRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 10,
  },
  warningIcon: {
    width: 28,
    height: 28,
    borderRadius: Radius.sm,
    backgroundColor: "#FFFBEB",
    alignItems: "center",
    justifyContent: "center",
    marginTop: 1,
    flexShrink: 0,
  },
  warningText: {
    flex: 1,
    fontSize: 14,
    color: Colors.textPrimary,
    lineHeight: 21,
  },
  altLabel: {
    fontSize: 12,
    fontWeight: "600",
    color: Colors.textTertiary,
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  slotCard: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: Colors.primaryLight,
    borderRadius: Radius.md,
    paddingHorizontal: 12,
    paddingVertical: 10,
    gap: 10,
  },
  slotText: {
    flex: 1,
  },
  slotTime: {
    fontSize: 14,
    fontWeight: "600",
    color: Colors.textPrimary,
  },
  slotDate: {
    fontSize: 12,
    color: Colors.textSecondary,
    marginTop: 1,
  },
});
