import React, { useState, useEffect } from "react";
import { View, StyleSheet, Alert, ScrollView } from "react-native";
import { Text, FAB, ActivityIndicator, IconButton } from "react-native-paper";
import { Agenda, DateData, LocaleConfig } from "react-native-calendars";
import { MaterialIcons } from "@expo/vector-icons";
import * as Localization from "expo-localization";
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

interface AgendaItems {
  [date: string]: Event[];
}

export default function CalendarScreen() {
  const [events, setEvents] = useState<Event[]>([]);
  const [agendaItems, setAgendaItems] = useState<AgendaItems>({});
  const [allEventsByDate, setAllEventsByDate] = useState<AgendaItems>({}); // Store all events by date for timeline
  const [loading, setLoading] = useState(true);
  const [updateModalVisible, setUpdateModalVisible] = useState(false);
  const [selectedEvent, setSelectedEvent] = useState<Event | null>(null);
  const [addModalVisible, setAddModalVisible] = useState(false);
  const { getEvents, updateEvent, deleteEvent, addEvent } = useCalendarAPI();

  useEffect(() => {
    loadEvents();
  }, []);

  useEffect(() => {
    updateAgendaItems(events);
  }, [events]);

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

  const updateAgendaItems = (eventList: Event[]) => {
    const items: AgendaItems = {};

    // Group events by date
    eventList.forEach((event) => {
      const dateKey = getDateKey(event.startDate);
      if (!items[dateKey]) {
        items[dateKey] = [];
      }
      items[dateKey].push(event);
    });

    // Sort events within each date by start time
    Object.keys(items).forEach((dateKey) => {
      items[dateKey].sort((a, b) => {
        return (
          new Date(a.startDate).getTime() - new Date(b.startDate).getTime()
        );
      });
    });

    // Store all events by date for timeline rendering
    setAllEventsByDate(items);

    // Create timeline items - one item per day that represents the full timeline
    const timelineItems: AgendaItems = {};
    Object.keys(items).forEach((dateKey) => {
      if (items[dateKey].length > 0) {
        // Use the first event as the representative item for the day
        // The renderTimelineItem function will get all events for the day
        timelineItems[dateKey] = [items[dateKey][0]];
      }
    });

    // Add empty arrays for dates in current month and next/previous months to prevent loading issues
    const today = new Date();
    const currentYear = today.getFullYear();
    const currentMonth = today.getMonth() + 1;

    // Generate empty dates for current month and 2 months before/after
    for (let monthOffset = -2; monthOffset <= 2; monthOffset++) {
      const date = new Date(currentYear, currentMonth - 1 + monthOffset, 1);
      const year = date.getFullYear();
      const month = date.getMonth() + 1;
      const daysInMonth = new Date(year, month, 0).getDate();

      for (let day = 1; day <= daysInMonth; day++) {
        const dateKey = `${year}-${month.toString().padStart(2, "0")}-${day
          .toString()
          .padStart(2, "0")}`;
        if (!timelineItems[dateKey]) {
          timelineItems[dateKey] = [];
        }
      }
    }

    // Store the timeline items for Agenda
    setAgendaItems(timelineItems);
  };

  const loadItemsForMonth = (month: any) => {
    // This function is called by Agenda to load items for a specific month
    // We need to ensure that for any date without events, we add an empty array
    // to prevent infinite loading

    const year = month.year;
    const monthNum = month.month;
    const daysInMonth = new Date(year, monthNum, 0).getDate();

    setTimeout(() => {
      const newItems = { ...agendaItems };

      // Add empty arrays for all dates in the month that don't have events
      for (let day = 1; day <= daysInMonth; day++) {
        const dateKey = `${year}-${monthNum.toString().padStart(2, "0")}-${day
          .toString()
          .padStart(2, "0")}`;
        if (!newItems[dateKey]) {
          newItems[dateKey] = [];
        }
      }

      setAgendaItems(newItems);
    }, 100);
  };

  // Use imported formatTime utility function

  const handleUpdateEvent = (event: Event) => {
    setSelectedEvent(event);
    setUpdateModalVisible(true);
  };

  const handleUpdateEventSubmit = async (
    eventId: string,
    updatedEvent: Partial<Event>
  ) => {
    try {
      const response = await updateEvent(eventId, updatedEvent);

      if (response) {
        // Update the events list with the updated event
        setEvents((prevEvents) =>
          prevEvents.map((event) => (event.id === eventId ? response : event))
        );
      }
    } catch (error) {
      console.error("Error updating event:", error);
      throw error;
    }
  };

  const handleDeleteEvent = (eventId: string) => {
    Alert.alert("Delete Event", "Are you sure you want to delete this event?", [
      {
        text: "Cancel",
        style: "cancel",
      },
      {
        text: "Delete",
        style: "destructive",
        onPress: async () => {
          try {
            await deleteEvent(eventId);

            // Remove from local state
            const updatedEvents = events.filter(
              (event) => event.id !== eventId
            );
            setEvents(updatedEvents);

            showSuccessToast("Event deleted successfully");
          } catch (error) {
            console.error("Error deleting event:", error);
            showErrorToast("Event could not be deleted");
          }
        },
      },
    ]);
  };

  const handleAddEvent = async (newEvent: EventCreate) => {
    try {
      const addedEvent = await addEvent(newEvent);

      const updatedEvents = [...events, addedEvent];
      setEvents(updatedEvents);
    } catch (error) {
      console.error("Error adding event:", error);
      throw error;
    }
  };

  const renderTimelineItem = (item: Event) => {
    // We'll render all events for the day in a timeline format
    // This function will be called once per day, so we need to get all events for that day
    const dateKey = getDateKey(item.startDate);
    const dayEvents = allEventsByDate[dateKey] || []; // Use allEventsByDate for timeline rendering

    // Create timeline with hour slots
    const timelineSlots = Array.from({ length: 24 }, (_, hour) => {
      const eventsAtThisHour = dayEvents.filter((event) => {
        const eventHour = new Date(event.startDate).getHours();
        return eventHour === hour;
      });

      return {
        hour,
        events: eventsAtThisHour,
      };
    });

    return (
      <View style={styles.timelineContainer}>
        <ScrollView
          style={styles.timelineScroll}
          showsVerticalScrollIndicator={false}
        >
          {timelineSlots.map((slot) => (
            <View key={slot.hour} style={styles.timeSlot}>
              {/* Hour label */}
              <View style={styles.hourLabelContainer}>
                <Text style={styles.hourLabel}>
                  {slot.hour.toString().padStart(2, "0")}:00
                </Text>
              </View>

              {/* Events for this hour */}
              <View style={styles.eventsContainer}>
                {slot.events.length === 0 ? (
                  <View style={styles.emptyHourSlot} />
                ) : (
                  slot.events.map((event) => {
                    const startDate = new Date(event.startDate);
                    // Don't add default duration - use actual duration or 0
                    const durationInMinutes = event.duration || 0;
                    const endDate = new Date(
                      startDate.getTime() + durationInMinutes * 60000
                    );

                    return (
                      <View key={event.id} style={styles.eventCard}>
                        <View style={styles.eventHeader}>
                          <View style={styles.eventTitleContainer}>
                            <Text style={styles.eventTitle}>{event.title}</Text>
                            <View style={styles.eventTimeContainer}>
                              <MaterialIcons
                                name="access-time"
                                size={14}
                                color="#6200ee"
                              />
                              <Text style={styles.eventTime}>
                                {durationInMinutes > 0
                                  ? `${formatTime(
                                      event.startDate
                                    )} - ${formatTime(endDate.toISOString())}`
                                  : formatTime(event.startDate)}
                              </Text>
                            </View>
                          </View>
                          <View style={styles.eventActions}>
                            <IconButton
                              icon={() => (
                                <MaterialIcons
                                  name="edit"
                                  size={18}
                                  color="#6200ee"
                                />
                              )}
                              onPress={() => handleUpdateEvent(event)}
                              style={styles.actionButton}
                            />
                            <IconButton
                              icon={() => (
                                <MaterialIcons
                                  name="delete"
                                  size={18}
                                  color="#ff4444"
                                />
                              )}
                              onPress={() => handleDeleteEvent(event.id)}
                              style={styles.actionButton}
                            />
                          </View>
                        </View>

                        <View style={styles.eventDetails}>
                          <View style={styles.eventDetailRow}>
                            <MaterialIcons
                              name="timer"
                              size={16}
                              color="#666"
                            />
                            <Text style={styles.eventDetailText}>
                              {formatDuration(event.duration)}
                            </Text>
                          </View>

                          <View style={styles.eventDetailRow}>
                            <MaterialIcons
                              name="location-on"
                              size={16}
                              color="#666"
                            />
                            <Text style={styles.eventDetailText}>
                              {formatLocation(event.location)}
                            </Text>
                          </View>
                        </View>
                      </View>
                    );
                  })
                )}
              </View>
            </View>
          ))}
        </ScrollView>
      </View>
    );
  };

  const renderEmptyDate = () => {
    return (
      <View style={styles.emptyDateContainer}>
        <MaterialIcons
          name="event-busy"
          size={48}
          color="#ccc"
          style={styles.emptyIcon}
        />
        <Text style={styles.emptyText}>
          There is no event planned for this date
        </Text>
      </View>
    );
  };

  return (
    <View style={styles.container}>
      {loading ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator animating={loading} color="#6200ee" size="large" />
        </View>
      ) : (
        <Agenda
          items={agendaItems}
          selected={new Date().toISOString().split("T")[0]}
          renderItem={renderTimelineItem}
          renderEmptyDate={renderEmptyDate}
          showClosingKnob={true}
          refreshControl={null}
          refreshing={false}
          loadItemsForMonth={loadItemsForMonth}
          showOnlySelectedDayItems={true}
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
            backgroundColor: "#f5f5f5",
            calendarBackground: "#ffffff",
          }}
        />
      )}

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
  eventCard: {
    backgroundColor: "#fff",
    marginHorizontal: 16,
    marginTop: 17,
    padding: 16,
    borderRadius: 8,
    elevation: 3,
    shadowColor: "#000",
    shadowOffset: {
      width: 0,
      height: 2,
    },
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
    justifyContent: "flex-end",
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
    padding: 20,
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
  timelineContainer: {
    flex: 1,
    backgroundColor: "#f5f5f5",
  },
  timelineScroll: {
    flex: 1,
  },
  timeSlot: {
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderBottomWidth: 1,
    borderBottomColor: "#eee",
  },
  hourLabelContainer: {
    marginBottom: 10,
  },
  hourLabel: {
    fontSize: 12,
    color: "#666",
    fontWeight: "bold",
  },
  eventsContainer: {
    // This container will hold all events for the current hour
    // Events will be positioned relative to this container
  },
  emptyHourSlot: {
    height: 60, // Space for hour label and potential future events
  },
});
