import React from "react";
import { View, StyleSheet } from "react-native";
import { Text } from "react-native-paper";
import { MaterialIcons } from "@expo/vector-icons";

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

export default function ConflictComponent({
  conflictMessage,
  suggestions,
}: ConflictComponentProps) {
  // Show only the first sentence (e.g. "There's a conflict with 'X'.")
  const headline = conflictMessage.split("\n")[0];

  return (
    <View style={styles.container}>
      {/* Conflict warning */}
      <View style={styles.warningRow}>
        <MaterialIcons name="warning" size={18} color="#ffcc00" />
        <Text style={styles.warningText}>{headline}</Text>
      </View>

      {suggestions.length > 0 && (
        <>
          <Text style={styles.altLabel}>Available times:</Text>
          {suggestions.map((s, i) => {
            const start = formatDateTime(s.startDate);
            const end = formatDateTime(s.endDate);
            const sameDay = start.date === end.date;
            return (
              <View key={i} style={styles.slotCard}>
                <MaterialIcons name="schedule" size={16} color="#a78bfa" style={styles.slotIcon} />
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
    gap: 8,
  },
  warningRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 8,
  },
  warningText: {
    flex: 1,
    fontSize: 15,
    color: "rgba(255,255,255,0.95)",
    lineHeight: 21,
  },
  altLabel: {
    fontSize: 13,
    color: "rgba(255,255,255,0.6)",
    marginTop: 4,
  },
  slotCard: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "rgba(255,255,255,0.12)",
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    gap: 10,
  },
  slotIcon: {
    marginTop: 1,
  },
  slotText: {
    flex: 1,
  },
  slotTime: {
    fontSize: 15,
    fontWeight: "600",
    color: "white",
  },
  slotDate: {
    fontSize: 13,
    color: "rgba(255,255,255,0.65)",
    marginTop: 2,
  },
});
