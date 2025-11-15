import React, { useState } from "react";
import { View, StyleSheet, TouchableOpacity } from "react-native";
import { Text, Card, Button, Divider } from "react-native-paper";
import { MaterialIcons } from "@expo/vector-icons";
import UpdateAgentEventModal from "./UpdateAgentEventModal";
import { Event } from "../models/event";
import { formatDuration, formatLocation } from "../common/formatting";
import {
  formatDateTime,
  formatConflictEventDate,
} from "../utils/datetime/dateUtils";

interface UpdateComponentProps {
  events: Event[];
  updateArguments: any;
  onUpdate: (eventId: string, updatedEvent: any) => Promise<void>;
  onCompleted: () => void;
  conflictEvent?: Event; // Add conflict event prop
}

export default function UpdateComponent({
  events,
  updateArguments,
  onUpdate,
  onCompleted,
  conflictEvent,
}: UpdateComponentProps) {
  const [selectedEvent, setSelectedEvent] = useState<Event | null>(null);
  const [modalVisible, setModalVisible] = useState(false);
  const [isCompleted, setIsCompleted] = useState(false);

  const handleEventPress = (event: Event) => {
    if (isCompleted) return;
    setSelectedEvent(event);
    setModalVisible(true);
  };

  const handleUpdate = async (eventId: string, updatedEvent: any) => {
    try {
      await onUpdate(eventId, updatedEvent);
      setModalVisible(false);
      setSelectedEvent(null);
      setIsCompleted(true);
      onCompleted();
    } catch (error) {
      console.error("Error updating event:", error);
    }
  };

  const handleCancel = () => {
    setIsCompleted(true);
    onCompleted();
  };

  // Use imported date utility functions for consistent formatting
  const formatDateTimeWithFallback = (datetime: string) => {
    if (!datetime) return "Date not specified";
    return formatDateTime(datetime);
  };

  const renderEventCard = (event: Event) => (
    <TouchableOpacity
      key={event.id}
      onPress={() => handleEventPress(event)}
      style={styles.eventCard}
      disabled={isCompleted}
    >
      <Card style={[styles.card, isCompleted && styles.disabledCard]}>
        <Card.Content>
          <View style={styles.eventHeader}>
            <Text
              style={[styles.eventTitle, isCompleted && styles.disabledText]}
            >
              {event.title}
            </Text>
            <MaterialIcons
              name="edit"
              size={20}
              color={isCompleted ? "rgba(255, 255, 255, 0.3)" : "#6200ee"}
            />
          </View>

          <View style={styles.eventDetails}>
            <View style={styles.detailRow}>
              <MaterialIcons
                name="access-time"
                size={16}
                color={isCompleted ? "rgba(255, 255, 255, 0.3)" : "#666"}
              />
              <Text
                style={[styles.detailText, isCompleted && styles.disabledText]}
              >
                {formatDateTimeWithFallback(event.startDate)}
              </Text>
            </View>

            <View style={styles.detailRow}>
              <MaterialIcons
                name="timer"
                size={16}
                color={isCompleted ? "rgba(255, 255, 255, 0.3)" : "#666"}
              />
              <Text
                style={[styles.detailText, isCompleted && styles.disabledText]}
              >
                {formatDuration(event.duration)}
              </Text>
            </View>

            <View style={styles.detailRow}>
              <MaterialIcons
                name="location-on"
                size={16}
                color={isCompleted ? "rgba(255, 255, 255, 0.3)" : "#666"}
              />
              <Text
                style={[styles.detailText, isCompleted && styles.disabledText]}
              >
                {formatLocation(event.location)}
              </Text>
            </View>
          </View>
        </Card.Content>
      </Card>
    </TouchableOpacity>
  );

  return (
    <View style={styles.container}>
      <Text style={styles.headerText}>
        Select the event you want to update:
      </Text>

      {conflictEvent && (
        <Card style={styles.conflictCard}>
          <Card.Content>
            <View style={styles.conflictHeader}>
              <MaterialIcons name="warning" size={20} color="#ff4444" />
              <Text style={styles.conflictWarning}>
                There is a conflict with this event
              </Text>
            </View>
            <View style={styles.conflictDetails}>
              <Text style={styles.conflictEventTitle}>
                {conflictEvent.title}
              </Text>
              <Text style={styles.conflictEventTime}>
                {formatConflictEventDate(
                  conflictEvent.startDate,
                  conflictEvent.duration
                )}
              </Text>
              {conflictEvent.location && (
                <Text style={styles.conflictEventLocation}>
                  {conflictEvent.location}
                </Text>
              )}
            </View>
          </Card.Content>
        </Card>
      )}

      {Object.keys(updateArguments).length > 0 && (
        <View style={styles.updatePreview}>
          <Divider style={styles.divider} />
          <Text style={styles.updatePreviewTitle}>Values to be updated:</Text>

          {updateArguments.title && (
            <View style={styles.updateItem}>
              <Text style={styles.updateLabel}>Title:</Text>
              <Text style={styles.updateValue}>{updateArguments.title}</Text>
            </View>
          )}

          {updateArguments.startDate && (
            <View style={styles.updateItem}>
              <Text style={styles.updateLabel}>Date & Time:</Text>
              <Text style={styles.updateValue}>
                {formatDateTimeWithFallback(updateArguments.startDate)}
              </Text>
            </View>
          )}

          {updateArguments.duration !== null &&
            updateArguments.duration !== undefined && (
              <View style={styles.updateItem}>
                <Text style={styles.updateLabel}>Duration:</Text>
                <Text style={styles.updateValue}>
                  {formatDuration(updateArguments.duration)}
                </Text>
              </View>
            )}

          {updateArguments.location && (
            <View style={styles.updateItem}>
              <Text style={styles.updateLabel}>Location:</Text>
              <Text style={styles.updateValue}>
                {formatLocation(updateArguments.location)}
              </Text>
            </View>
          )}
        </View>
      )}

      <View>{events.map(renderEventCard)}</View>

      <View style={styles.buttonContainer}>
        <Button
          mode="outlined"
          onPress={handleCancel}
          style={[styles.cancelButton, isCompleted && styles.disabledButton]}
          contentStyle={styles.buttonContent}
          disabled={isCompleted}
        >
          Cancel
        </Button>
      </View>

      {selectedEvent && (
        <UpdateAgentEventModal
          visible={modalVisible}
          event={selectedEvent}
          updateArguments={updateArguments}
          onDismiss={() => {
            setModalVisible(false);
            setSelectedEvent(null);
          }}
          onUpdate={handleUpdate}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginTop: 12,
  },
  headerText: {
    fontSize: 16,
    fontWeight: "600",
    color: "rgba(255, 255, 255, 0.9)",
    marginBottom: 12,
  },
  eventCard: {
    marginBottom: 8,
  },
  card: {
    backgroundColor: "rgba(255, 255, 255, 0.1)",
    borderRadius: 12,
  },
  disabledCard: {
    opacity: 0.5,
  },
  eventHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 8,
  },
  eventTitle: {
    fontSize: 16,
    fontWeight: "600",
    color: "white",
    flex: 1,
  },
  disabledText: {
    color: "rgba(255, 255, 255, 0.3)",
  },
  eventDetails: {
    marginBottom: 8,
  },
  detailRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 4,
  },
  detailText: {
    fontSize: 14,
    color: "rgba(255, 255, 255, 0.8)",
    marginLeft: 8,
  },
  updatePreview: {
    marginBottom: 8,
  },
  divider: {
    backgroundColor: "rgba(255, 255, 255, 0.2)",
    marginBottom: 8,
  },
  updatePreviewTitle: {
    fontSize: 14,
    fontWeight: "600",
    color: "#81C784",
    marginBottom: 6,
  },
  updateItem: {
    flexDirection: "row",
    marginBottom: 4,
  },
  updateLabel: {
    fontSize: 12,
    color: "rgba(255, 255, 255, 0.7)",
    width: 80,
  },
  updateValue: {
    fontSize: 12,
    color: "#81C784",
    fontWeight: "500",
    flex: 1,
  },
  buttonContainer: {
    marginTop: 16,
  },
  cancelButton: {
    borderColor: "rgba(255, 255, 255, 0.3)",
    borderWidth: 1,
  },
  disabledButton: {
    opacity: 0.5,
    borderColor: "rgba(255, 255, 255, 0.1)",
  },
  buttonContent: {
    paddingVertical: 4,
  },
  conflictCard: {
    backgroundColor: "rgba(255, 255, 255, 0.05)",
    borderRadius: 12,
    marginTop: 8,
    marginBottom: 8,
    borderColor: "#ff4444",
    borderWidth: 1,
  },
  conflictHeader: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 8,
  },
  conflictWarning: {
    fontSize: 14,
    fontWeight: "600",
    color: "#ff4444",
    marginLeft: 8,
  },
  conflictDetails: {
    marginLeft: 20,
  },
  conflictEventTitle: {
    fontSize: 14,
    fontWeight: "600",
    color: "white",
    marginBottom: 4,
  },
  conflictEventTime: {
    fontSize: 12,
    color: "rgba(255, 255, 255, 0.7)",
    marginBottom: 4,
  },
  conflictEventLocation: {
    fontSize: 12,
    color: "rgba(255, 255, 255, 0.7)",
  },
});
