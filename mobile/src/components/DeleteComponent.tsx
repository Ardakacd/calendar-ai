import React, { useState, useEffect } from "react";
import { View, StyleSheet, TouchableOpacity } from "react-native";
import { Card, Text, Button } from "react-native-paper";
import { MaterialIcons } from "@expo/vector-icons";
import { Event } from "../models/event";
import { formatDuration, formatLocation } from "../common/formatting";
import { formatDateWithWeekday } from "../utils/datetime/dateUtils";

interface DeleteComponentProps {
  events: Event[];
  onDelete: (eventIds: string[]) => Promise<void>;
  onCompleted: () => void;
}

export default function DeleteComponent({
  events,
  onDelete,
  onCompleted,
}: DeleteComponentProps) {
  const [selectedEvents, setSelectedEvents] = useState<Set<string>>(new Set());
  const [isDeleting, setIsDeleting] = useState(false);
  const [isCompleted, setIsCompleted] = useState(false);

  // Use imported date utility function for consistent formatting

  const handleEventPress = (event: Event) => {
    if (isCompleted) return;

    const newSelectedEvents = new Set(selectedEvents);
    if (newSelectedEvents.has(event.id)) {
      newSelectedEvents.delete(event.id);
    } else {
      newSelectedEvents.add(event.id);
    }
    setSelectedEvents(newSelectedEvents);
  };

  const handleSelectAll = () => {
    if (isCompleted) return;
    const allEventIds = events.map((event) => event.id);
    setSelectedEvents(new Set(allEventIds));
  };

  const handleDeselectAll = () => {
    if (isCompleted) return;
    setSelectedEvents(new Set());
  };

  const handleDelete = async () => {
    if (selectedEvents.size === 0) return;

    setIsDeleting(true);
    try {
      const eventIds = Array.from(selectedEvents);
      await onDelete(eventIds);
      setIsCompleted(true);
      onCompleted();
    } catch (error) {
      console.error("Error deleting events:", error);
    } finally {
      setIsDeleting(false);
    }
  };

  const handleCancel = () => {
    setIsCompleted(true);
    onCompleted();
  };

  if (!events || events.length === 0) {
    return null;
  }

  if (isCompleted) {
    return (
      <View style={styles.container}>
        <View style={styles.eventsContainer}>
          {events.map((event, index) => (
            <Card
              key={event.id}
              style={[
                styles.eventCard,
                index > 0 && styles.eventCardMargin,
                styles.disabledCard,
              ]}
            >
              <Card.Content>
                <View style={styles.eventHeader}>
                  <View style={styles.titleContainer}>
                    <MaterialIcons
                      name="radio-button-unchecked"
                      size={20}
                      color="rgba(255, 255, 255, 0.3)"
                      style={styles.selectionIcon}
                    />
                    <Text
                      style={[styles.eventTitle, styles.disabledText]}
                      numberOfLines={2}
                    >
                      {event.title}
                    </Text>
                  </View>
                </View>

                <View style={styles.eventDetails}>
                  <View style={styles.detailRow}>
                    <MaterialIcons
                      name="schedule"
                      size={16}
                      color="rgba(255, 255, 255, 0.3)"
                    />
                    <Text style={[styles.detailText, styles.disabledText]}>
                      {formatDateWithWeekday(event.startDate)}
                    </Text>
                  </View>

                  <View style={styles.detailRow}>
                    <MaterialIcons
                      name="timer"
                      size={16}
                      color="rgba(255, 255, 255, 0.3)"
                    />
                    <Text style={[styles.detailText, styles.disabledText]}>
                      {formatDuration(event.duration)}
                    </Text>
                  </View>

                  <View style={styles.detailRow}>
                    <MaterialIcons
                      name="location-on"
                      size={16}
                      color="rgba(255, 255, 255, 0.3)"
                    />
                    <Text
                      style={[styles.detailText, styles.disabledText]}
                      numberOfLines={1}
                    >
                      {formatLocation(event.location)}
                    </Text>
                  </View>
                </View>
              </Card.Content>
            </Card>
          ))}
        </View>

        <View style={styles.actionButtons}>
          <Button
            mode="contained"
            disabled={true}
            style={[styles.deleteButton, styles.disabledButton]}
            labelStyle={[styles.deleteButtonText, styles.disabledText]}
            icon="delete"
          >
            Delete
          </Button>
          <Button
            mode="outlined"
            disabled={true}
            style={[styles.cancelButton, styles.disabledButton]}
            labelStyle={[styles.cancelButtonText, styles.disabledText]}
            icon="close"
          >
            Cancel
          </Button>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.selectionControls}>
        <Button
          mode="text"
          onPress={handleSelectAll}
          disabled={isDeleting}
          style={styles.selectionButton}
          labelStyle={styles.selectionButtonText}
        >
          Select All
        </Button>
        <Button
          mode="text"
          onPress={handleDeselectAll}
          disabled={isDeleting}
          style={styles.selectionButton}
          labelStyle={styles.selectionButtonText}
        >
          Remove Selection
        </Button>
      </View>

      <View style={styles.eventsContainer}>
        {events.map((event, index) => {
          const isSelected = selectedEvents.has(event.id);

          return (
            <TouchableOpacity
              key={event.id}
              onPress={() => handleEventPress(event)}
              activeOpacity={0.7}
            >
              <Card
                style={[
                  styles.eventCard,
                  index > 0 && styles.eventCardMargin,
                  isSelected && styles.selectedEventCard,
                ]}
              >
                <Card.Content>
                  <View style={styles.eventHeader}>
                    <View style={styles.titleContainer}>
                      <MaterialIcons
                        name={
                          isSelected ? "check-circle" : "radio-button-unchecked"
                        }
                        size={20}
                        color={
                          isSelected ? "#4ecdc4" : "rgba(255, 255, 255, 0.5)"
                        }
                        style={styles.selectionIcon}
                      />
                      <Text
                        style={[
                          styles.eventTitle,
                          isSelected && styles.selectedEventTitle,
                        ]}
                        numberOfLines={2}
                      >
                        {event.title}
                      </Text>
                    </View>
                  </View>

                  <View style={styles.eventDetails}>
                    <View style={styles.detailRow}>
                      <MaterialIcons
                        name="schedule"
                        size={16}
                        color="rgba(255, 255, 255, 0.7)"
                      />
                      <Text style={styles.detailText}>
                        {formatDateWithWeekday(event.startDate)}
                      </Text>
                    </View>

                    <View style={styles.detailRow}>
                      <MaterialIcons
                        name="timer"
                        size={16}
                        color="rgba(255, 255, 255, 0.7)"
                      />
                      <Text style={styles.detailText}>
                        {formatDuration(event.duration)}
                      </Text>
                    </View>

                    <View style={styles.detailRow}>
                      <MaterialIcons
                        name="location-on"
                        size={16}
                        color="rgba(255, 255, 255, 0.7)"
                      />
                      <Text style={styles.detailText} numberOfLines={1}>
                        {formatLocation(event.location)}
                      </Text>
                    </View>
                  </View>
                </Card.Content>
              </Card>
            </TouchableOpacity>
          );
        })}
      </View>

      <View style={styles.actionButtons}>
        <Button
          mode="contained"
          onPress={handleDelete}
          loading={isDeleting}
          disabled={isDeleting || selectedEvents.size === 0}
          style={[
            styles.deleteButton,
            selectedEvents.size === 0 && styles.disabledButton,
          ]}
          labelStyle={[
            styles.deleteButtonText,
            selectedEvents.size === 0 && styles.disabledText,
          ]}
          icon="delete"
        >
          Delete
        </Button>
        <Button
          mode="outlined"
          onPress={handleCancel}
          disabled={isDeleting}
          style={styles.cancelButton}
          labelStyle={styles.cancelButtonText}
          icon="close"
        >
          Cancel
        </Button>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginTop: 12,
  },
  instructionText: {
    fontSize: 14,
    color: "rgba(255, 255, 255, 0.9)",
    marginBottom: 12,
    textAlign: "center",
  },
  eventsContainer: {
    marginBottom: 16,
  },
  eventCard: {
    backgroundColor: "rgba(255, 255, 255, 0.1)",
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "rgba(255, 255, 255, 0.1)",
  },
  selectedEventCard: {
    backgroundColor: "rgba(78, 205, 196, 0.2)",
    borderColor: "#4ecdc4",
    borderWidth: 2,
  },
  eventCardMargin: {
    marginTop: 8,
  },
  emptyCard: {
    backgroundColor: "rgba(255, 255, 255, 0.05)",
    borderRadius: 12,
    marginTop: 8,
  },
  emptyText: {
    color: "rgba(255, 255, 255, 0.6)",
    textAlign: "center",
    fontSize: 14,
  },
  eventHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: 12,
  },
  titleContainer: {
    flex: 1,
    flexDirection: "row",
    alignItems: "flex-start",
    marginRight: 8,
  },
  selectionIcon: {
    marginRight: 8,
    marginTop: 2,
  },
  eventTitle: {
    fontSize: 16,
    fontWeight: "600",
    color: "white",
    flex: 1,
    lineHeight: 20,
  },
  selectedEventTitle: {
    color: "#4ecdc4",
  },
  eventDetails: {
    gap: 8,
  },
  detailRow: {
    flexDirection: "row",
    alignItems: "center",
  },
  detailText: {
    fontSize: 14,
    color: "rgba(255, 255, 255, 0.8)",
    marginLeft: 8,
    flex: 1,
  },
  actionButtons: {
    flexDirection: "row",
    gap: 12,
    justifyContent: "center",
  },
  deleteButton: {
    backgroundColor: "#ff6b6b",
    borderRadius: 8,
    flex: 1,
  },
  deleteButtonText: {
    color: "white",
    fontSize: 14,
    fontWeight: "600",
  },
  cancelButton: {
    borderColor: "rgba(255, 255, 255, 0.3)",
    borderRadius: 8,
    flex: 1,
  },
  cancelButtonText: {
    color: "rgba(255, 255, 255, 0.8)",
    fontSize: 14,
  },
  disabledCard: {
    opacity: 0.5,
    backgroundColor: "rgba(255, 255, 255, 0.05)",
    borderColor: "rgba(255, 255, 255, 0.05)",
  },
  disabledButton: {
    opacity: 0.5,
    backgroundColor: "rgba(255, 255, 255, 0.05)",
    borderColor: "rgba(255, 255, 255, 0.05)",
  },
  disabledText: {
    color: "rgba(255, 255, 255, 0.3)",
  },
  selectionControls: {
    flexDirection: "row",
    justifyContent: "space-around",
    marginBottom: 12,
  },
  selectionButton: {
    paddingHorizontal: 10,
    paddingVertical: 5,
  },
  selectionButtonText: {
    color: "rgba(255, 255, 255, 0.8)",
    fontSize: 14,
  },
});
