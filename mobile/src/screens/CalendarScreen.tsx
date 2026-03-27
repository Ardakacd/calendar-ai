import React, { useState, useEffect, useMemo, useCallback } from "react";
import { View, StyleSheet, Alert, FlatList } from "react-native";
import { Text, FAB, ActivityIndicator, IconButton } from "react-native-paper";
import { Calendar, DateData } from "react-native-calendars";
import { MaterialIcons } from "@expo/vector-icons";
import { useCalendarAPI } from "../services/api";
import UpdateEventModal from "../components/UpdateEventModal";
import AddEventModal from "../components/AddEventModal";
import { Event, EventCreate } from "../models/event";
import { formatDuration, formatLocation } from "../common/formatting";
import { formatTime, getDateKey } from "../utils/datetime/dateUtils";
import {
  showErrorToast,
  showSuccessToast,
} from "../common/toast/toast-message";

export default function CalendarScreen() {
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDate, setSelectedDate] = useState(
    new Date().toISOString().split("T")[0]
  );
  const [updateModalVisible, setUpdateModalVisible] = useState(false);
  const [selectedEvent, setSelectedEvent] = useState<Event | null>(null);
  const [addModalVisible, setAddModalVisible] = useState(false);
  const { getEvents, updateEvent, deleteEvent, addEvent } = useCalendarAPI();

  useEffect(() => {
    loadEvents();
  }, []);

  const loadEvents = async () => {
    try {
      setLoading(true);
      const fetchedEvents = await getEvents();
      setEvents(fetchedEvents);
    } catch (error) {
      showErrorToast("Events could not be loaded");
    } finally {
      setLoading(false);
    }
  };

  // Build marked dates for the calendar dots
  const markedDates = useMemo(() => {
    const marks: Record<string, any> = {};
    events.forEach((event) => {
      const key = getDateKey(event.startDate);
      marks[key] = { marked: true, dotColor: "#6200ee" };
    });
    // Highlight selected date
    marks[selectedDate] = {
      ...(marks[selectedDate] || {}),
      selected: true,
      selectedColor: "#6200ee",
    };
    return marks;
  }, [events, selectedDate]);

  // Events for the selected day
  const selectedDayEvents = useMemo(() => {
    return events
      .filter((e) => getDateKey(e.startDate) === selectedDate)
      .sort(
        (a, b) =>
          new Date(a.startDate).getTime() - new Date(b.startDate).getTime()
      );
  }, [events, selectedDate]);

  const handleDayPress = useCallback((day: DateData) => {
    setSelectedDate(day.dateString);
  }, []);

  const handleUpdateEvent = useCallback((event: Event) => {
    setSelectedEvent(event);
    setUpdateModalVisible(true);
  }, []);

  const handleUpdateEventSubmit = async (
    eventId: string,
    updatedEvent: Partial<Event>
  ) => {
    try {
      const response = await updateEvent(eventId, updatedEvent);
      if (response) {
        setEvents((prev) =>
          prev.map((e) => (e.id === eventId ? response : e))
        );
      }
    } catch (error) {
      throw error;
    }
  };

  const handleDeleteEvent = useCallback(
    (eventId: string) => {
      Alert.alert(
        "Delete Event",
        "Are you sure you want to delete this event?",
        [
          { text: "Cancel", style: "cancel" },
          {
            text: "Delete",
            style: "destructive",
            onPress: async () => {
              try {
                await deleteEvent(eventId);
                setEvents((prev) => prev.filter((e) => e.id !== eventId));
                showSuccessToast("Event deleted successfully");
              } catch (error) {
                showErrorToast("Event could not be deleted");
              }
            },
          },
        ]
      );
    },
    [deleteEvent]
  );

  const handleAddEvent = async (newEvent: EventCreate) => {
    try {
      const addedEvent = await addEvent(newEvent);
      setEvents((prev) => [...prev, addedEvent]);
    } catch (error) {
      throw error;
    }
  };

  const renderEventCard = useCallback(
    ({ item: event }: { item: Event }) => {
      const startDate = new Date(event.startDate);
      const durationInMinutes = event.duration || 0;
      const endDate = new Date(startDate.getTime() + durationInMinutes * 60000);

      return (
        <View style={styles.eventCard}>
          <View style={styles.eventHeader}>
            <View style={styles.eventTitleContainer}>
              <Text style={styles.eventTitle}>{event.title}</Text>
              <View style={styles.eventTimeContainer}>
                <MaterialIcons name="access-time" size={14} color="#6200ee" />
                <Text style={styles.eventTime}>
                  {durationInMinutes > 0
                    ? `${formatTime(event.startDate)} - ${formatTime(
                        endDate.toISOString()
                      )}`
                    : formatTime(event.startDate)}
                </Text>
              </View>
            </View>
            <View style={styles.eventActions}>
              <IconButton
                icon={() => (
                  <MaterialIcons name="edit" size={18} color="#6200ee" />
                )}
                onPress={() => handleUpdateEvent(event)}
                style={styles.actionButton}
              />
              <IconButton
                icon={() => (
                  <MaterialIcons name="delete" size={18} color="#ff4444" />
                )}
                onPress={() => handleDeleteEvent(event.id)}
                style={styles.actionButton}
              />
            </View>
          </View>

          <View style={styles.eventDetails}>
            <View style={styles.eventDetailRow}>
              <MaterialIcons name="timer" size={16} color="#666" />
              <Text style={styles.eventDetailText}>
                {formatDuration(event.duration)}
              </Text>
            </View>
            <View style={styles.eventDetailRow}>
              <MaterialIcons name="location-on" size={16} color="#666" />
              <Text style={styles.eventDetailText}>
                {formatLocation(event.location)}
              </Text>
            </View>
          </View>
        </View>
      );
    },
    [handleUpdateEvent, handleDeleteEvent]
  );

  const renderEmptyDay = () => (
    <View style={styles.emptyDateContainer}>
      <MaterialIcons
        name="event-busy"
        size={48}
        color="#ccc"
        style={styles.emptyIcon}
      />
      <Text style={styles.emptyText}>No events planned for this day</Text>
    </View>
  );

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator animating color="#6200ee" size="large" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Calendar
        onDayPress={handleDayPress}
        markedDates={markedDates}
        theme={{
          todayTextColor: "#6200ee",
          dayTextColor: "#2d4150",
          textDisabledColor: "#d9e1e8",
          dotColor: "#6200ee",
          selectedDotColor: "#ffffff",
          arrowColor: "#6200ee",
          monthTextColor: "#2d4150",
          indicatorColor: "#6200ee",
          textDayFontWeight: "300",
          textMonthFontWeight: "bold",
          textDayHeaderFontWeight: "300",
          textDayFontSize: 16,
          textMonthFontSize: 16,
          textDayHeaderFontSize: 13,
          backgroundColor: "#ffffff",
          calendarBackground: "#ffffff",
        }}
      />

      <FlatList
        data={selectedDayEvents}
        keyExtractor={(item) => item.id}
        renderItem={renderEventCard}
        ListEmptyComponent={renderEmptyDay}
        contentContainerStyle={styles.listContent}
        style={styles.list}
      />

      <FAB
        style={styles.fab}
        icon={() => <MaterialIcons name="add" size={24} color="white" />}
        color="white"
        onPress={() => setAddModalVisible(true)}
        label="Add Event"
      />

      <UpdateEventModal
        visible={updateModalVisible}
        event={selectedEvent}
        onDismiss={() => {
          setUpdateModalVisible(false);
          setSelectedEvent(null);
        }}
        onUpdate={handleUpdateEventSubmit}
      />

      <AddEventModal
        visible={addModalVisible}
        onDismiss={() => setAddModalVisible(false)}
        onAdd={handleAddEvent}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#f5f5f5",
  },
  loadingContainer: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "#f5f5f5",
  },
  list: {
    flex: 1,
  },
  listContent: {
    paddingHorizontal: 16,
    paddingTop: 8,
    paddingBottom: 80,
  },
  eventCard: {
    backgroundColor: "#fff",
    marginVertical: 6,
    padding: 16,
    borderRadius: 8,
    elevation: 3,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  eventHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: 8,
  },
  eventTitleContainer: {
    flex: 1,
    marginRight: 12,
  },
  eventTitle: {
    fontSize: 18,
    fontWeight: "600",
    color: "#333",
  },
  eventTimeContainer: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: 4,
  },
  eventTime: {
    fontSize: 14,
    color: "#666",
    marginLeft: 4,
  },
  eventActions: {
    flexDirection: "row",
    alignItems: "center",
  },
  actionButton: {
    marginLeft: -8,
  },
  eventDetails: {
    marginTop: 8,
  },
  eventDetailRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 4,
  },
  eventDetailText: {
    fontSize: 14,
    color: "#666",
    marginLeft: 8,
  },
  emptyDateContainer: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    paddingTop: 40,
  },
  emptyIcon: {
    marginBottom: 10,
  },
  emptyText: {
    fontSize: 16,
    color: "#999",
    textAlign: "center",
  },
  fab: {
    position: "absolute",
    margin: 16,
    right: 0,
    bottom: 0,
    backgroundColor: "#6200ee",
  },
});
