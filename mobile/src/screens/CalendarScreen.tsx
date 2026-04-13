import React, { useState, useEffect, useRef, useMemo, useCallback } from "react";
import { View, StyleSheet, Alert, FlatList, RefreshControl, AppState } from "react-native";
import { Text, FAB, ActivityIndicator, IconButton } from "react-native-paper";
import { Calendar, DateData } from "react-native-calendars";
import { useFocusEffect, useNavigation, useRoute, RouteProp } from "@react-navigation/native";
import type { StackNavigationProp } from "@react-navigation/stack";
import type { RootStackParamList } from "../navigation/types";
import { MaterialIcons } from "@expo/vector-icons";
import { useCalendarAPI } from "../services/api";
import UpdateEventModal from "../components/UpdateEventModal";
import AddEventModal from "../components/AddEventModal";
import { Event, EventCreate, SeriesUpdateRequest } from "../models/event";
import { formatDuration, formatLocation } from "../common/formatting";
import { formatCalendarDayHeading, formatTime, getDateKey } from "../utils/datetime/dateUtils";
import { showErrorToast, showSuccessToast } from "../common/toast/toast-message";
import { Colors, Radius, Shadow, getCategoryColor } from "../theme";

type CalendarRoute = RouteProp<RootStackParamList, "Calendar">;
type CalendarNavigation = StackNavigationProp<RootStackParamList, "Calendar">;

export default function CalendarScreen() {
  const route = useRoute<CalendarRoute>();
  const navigation = useNavigation<CalendarNavigation>();
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDate, setSelectedDate] = useState(
    new Date().toISOString().split("T")[0]
  );
  const [updateModalVisible, setUpdateModalVisible] = useState(false);
  const [selectedEvent, setSelectedEvent] = useState<Event | null>(null);
  const [addModalVisible, setAddModalVisible] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const { getEvents, getEventById, updateEvent, updateSeries, deleteEvent, deleteSeries, addEvent } = useCalendarAPI();

  const loadEvents = useCallback(async () => {
    try {
      setLoading(true);
      const fetchedEvents = await getEvents();
      setEvents(fetchedEvents);
    } catch {
      showErrorToast("Events could not be loaded");
    } finally {
      setLoading(false);
    }
  }, [getEvents]);

  // Deep link: fetch the specific event by ID and open it directly.
  // Uses a ref to guard against double-firing (strict mode / param flicker).
  const handledDeepLinkRef = useRef<string | undefined>(undefined);
  useEffect(() => {
    const eventId = route.params?.eventId;
    if (!eventId || eventId === handledDeepLinkRef.current) return;
    handledDeepLinkRef.current = eventId;
    navigation.setParams({ eventId: undefined });
    getEventById(eventId)
      .then((ev) => {
        const key = getDateKey(ev.startDate);
        if (key) setSelectedDate(key);
        setSelectedEvent(ev);
        setUpdateModalVisible(true);
      })
      .catch(() => {
        showErrorToast("Event not found or no longer available");
      });
  }, [route.params?.eventId, navigation, getEventById]); // eslint-disable-line react-hooks/exhaustive-deps

  useFocusEffect(
    useCallback(() => {
      loadEvents();
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [])
  );

  const appState = useRef(AppState.currentState);
  useEffect(() => {
    const sub = AppState.addEventListener("change", (nextState) => {
      if (appState.current.match(/inactive|background/) && nextState === "active") {
        loadEvents();
      }
      appState.current = nextState;
    });
    return () => sub.remove();
  }, [loadEvents]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    try {
      const fetchedEvents = await getEvents();
      setEvents(fetchedEvents);
    } catch {
      showErrorToast("Events could not be loaded");
    } finally {
      setRefreshing(false);
    }
  }, [getEvents]);

  const markedDates = useMemo(() => {
    const marks: Record<string, any> = {};
    const byDay = new Map<string, Event[]>();
    events.forEach((event) => {
      const key = getDateKey(event.startDate);
      if (!key) return;
      if (!byDay.has(key)) byDay.set(key, []);
      byDay.get(key)!.push(event);
    });
    byDay.forEach((dayEvents, key) => {
      const sorted = [...dayEvents].sort(
        (a, b) => new Date(a.startDate).getTime() - new Date(b.startDate).getTime()
      );
      const first = sorted[0];
      const dotColor = getCategoryColor(first.category).accent;
      marks[key] = { marked: true, dotColor };
    });
    marks[selectedDate] = {
      ...(marks[selectedDate] || {}),
      selected: true,
      selectedColor: Colors.primary,
    };
    return marks;
  }, [events, selectedDate]);

  const selectedDayEvents = useMemo(() => {
    return events
      .filter((e) => getDateKey(e.startDate) === selectedDate)
      .sort((a, b) => new Date(a.startDate).getTime() - new Date(b.startDate).getTime());
  }, [events, selectedDate]);

  const handleDayPress = useCallback((day: DateData) => {
    setSelectedDate(day.dateString);
  }, []);

  const handleUpdateEvent = useCallback((event: Event) => {
    setSelectedEvent(event);
    setUpdateModalVisible(true);
  }, []);

  const handleUpdateEventSubmit = async (eventId: string, updatedEvent: Partial<Event>) => {
    try {
      const response = await updateEvent(eventId, updatedEvent);
      if (response) {
        setEvents((prev) => prev.map((e) => (e.id === eventId ? response : e)));
      }
    } catch (error) {
      throw error;
    }
  };

  const handleUpdateSeriesSubmit = async (recurrenceId: string, request: SeriesUpdateRequest) => {
    try {
      await updateSeries(recurrenceId, request);
      // Reload all events so every updated occurrence reflects the new data
      await loadEvents();
    } catch (error) {
      throw error;
    }
  };

  const handleDeleteEvent = useCallback(
    (event: Event) => {
      if (event.recurrence_id) {
        Alert.alert(
          "Delete Recurring Event",
          "Which occurrences do you want to delete?",
          [
            { text: "Cancel", style: "cancel" },
            {
              text: "This event only",
              onPress: async () => {
                try {
                  await deleteEvent(event.id);
                  setEvents((prev) => prev.filter((e) => e.id !== event.id));
                  showSuccessToast("Event deleted");
                } catch {
                  showErrorToast("Event could not be deleted");
                }
              },
            },
            {
              text: "This & future events",
              style: "destructive",
              onPress: async () => {
                try {
                  await deleteSeries(event.recurrence_id!, "future", event.startDate);
                  await loadEvents();
                  showSuccessToast("Future events deleted");
                } catch {
                  showErrorToast("Events could not be deleted");
                }
              },
            },
            {
              text: "All events in series",
              style: "destructive",
              onPress: async () => {
                try {
                  await deleteSeries(event.recurrence_id!, "all");
                  await loadEvents();
                  showSuccessToast("All events in series deleted");
                } catch {
                  showErrorToast("Events could not be deleted");
                }
              },
            },
          ]
        );
      } else {
        Alert.alert("Delete Event", "Are you sure you want to delete this event?", [
          { text: "Cancel", style: "cancel" },
          {
            text: "Delete",
            style: "destructive",
            onPress: async () => {
              try {
                await deleteEvent(event.id);
                setEvents((prev) => prev.filter((e) => e.id !== event.id));
                showSuccessToast("Event deleted successfully");
              } catch {
                showErrorToast("Event could not be deleted");
              }
            },
          },
        ]);
      }
    },
    [deleteEvent, deleteSeries, loadEvents]
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

      const catColor = getCategoryColor(event.category);

      return (
        <View style={styles.eventCard}>
          <View style={[styles.eventAccent, { backgroundColor: catColor.accent }]} />
          <View style={styles.eventBody}>
            <View style={styles.eventTop}>
              <View style={styles.eventMeta}>
                <View style={styles.titleRow}>
                  <Text style={styles.eventTitle} numberOfLines={1}>
                    {event.title}
                  </Text>
                  {event.category ? (
                    <View style={[styles.categoryBadge, { backgroundColor: catColor.bg }]}>
                      <Text style={[styles.categoryBadgeText, { color: catColor.text }]}>
                        {event.category}
                      </Text>
                    </View>
                  ) : null}
                  {event.recurrence_type ? (
                    <View style={styles.recurrenceBadge}>
                      <MaterialIcons name="repeat" size={11} color={Colors.primary} />
                      <Text style={styles.recurrenceBadgeText}>{event.recurrence_type}</Text>
                    </View>
                  ) : null}
                </View>
                <View style={styles.timeRow}>
                  <MaterialIcons name="access-time" size={13} color={Colors.primary} />
                  <Text style={styles.eventTime}>
                    {durationInMinutes > 0
                      ? `${formatTime(event.startDate)} – ${formatTime(endDate.toISOString())}`
                      : formatTime(event.startDate)}
                  </Text>
                </View>
              </View>
              <View style={styles.eventActions}>
                <TouchableIconBtn
                  icon="edit"
                  color={Colors.primary}
                  onPress={() => handleUpdateEvent(event)}
                />
                <TouchableIconBtn
                  icon="delete-outline"
                  color={Colors.error}
                  onPress={() => handleDeleteEvent(event)}
                />
              </View>
            </View>

            {(event.duration || event.location) && (
              <View style={styles.eventDetails}>
                {event.duration ? (
                  <View style={styles.detailChip}>
                    <MaterialIcons name="timer" size={12} color={Colors.textTertiary} />
                    <Text style={styles.detailChipText}>{formatDuration(event.duration)}</Text>
                  </View>
                ) : null}
                {event.location ? (
                  <View style={styles.detailChip}>
                    <MaterialIcons name="location-on" size={12} color={Colors.textTertiary} />
                    <Text style={styles.detailChipText} numberOfLines={1}>
                      {formatLocation(event.location)}
                    </Text>
                  </View>
                ) : null}
              </View>
            )}
            {event.description ? (
              <Text style={styles.eventDescription} numberOfLines={2}>
                {event.description}
              </Text>
            ) : null}
          </View>
        </View>
      );
    },
    [handleUpdateEvent, handleDeleteEvent]
  );

  const renderEmptyDay = () => (
    <View style={styles.emptyState}>
      <View style={styles.emptyIconBox}>
        <MaterialIcons name="event-available" size={28} color={Colors.primary} />
      </View>
      <Text style={styles.emptyTitle}>Nothing scheduled</Text>
      <Text style={styles.emptySubtitle}>
        {formatCalendarDayHeading(selectedDate)} · Tap + to add an event
      </Text>
    </View>
  );

  if (loading && events.length === 0) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator animating color={Colors.primary} size="large" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.calendarWrapper}>
        <Calendar
          onDayPress={handleDayPress}
          markedDates={markedDates}
          enableSwipeMonths
          renderArrow={(direction) => (
            <View style={styles.arrowBtn}>
              <MaterialIcons
                name={direction === "left" ? "chevron-left" : "chevron-right"}
                size={20}
                color={Colors.primary}
              />
            </View>
          )}
          theme={{
            todayTextColor: Colors.primary,
            dayTextColor: Colors.textPrimary,
            textDisabledColor: Colors.textTertiary,
            dotColor: Colors.primary,
            selectedDotColor: Colors.surface,
            arrowColor: Colors.primary,
            monthTextColor: Colors.textPrimary,
            indicatorColor: Colors.primary,
            textDayFontWeight: "400",
            textMonthFontWeight: "700",
            textDayHeaderFontWeight: "500",
            textDayFontSize: 15,
            textMonthFontSize: 16,
            textDayHeaderFontSize: 12,
            backgroundColor: Colors.surface,
            calendarBackground: Colors.surface,
          }}
        />
      </View>

      <View style={styles.listHeader}>
        <Text style={styles.listHeaderDate}>{formatCalendarDayHeading(selectedDate)}</Text>
        <Text style={styles.listHeaderText}>
          {selectedDayEvents.length > 0
            ? `${selectedDayEvents.length} event${selectedDayEvents.length > 1 ? "s" : ""}`
            : "No events scheduled"}
        </Text>
      </View>

      <FlatList
        data={selectedDayEvents}
        keyExtractor={(item) => item.id}
        renderItem={renderEventCard}
        ListEmptyComponent={renderEmptyDay}
        contentContainerStyle={styles.listContent}
        style={styles.list}
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={Colors.primary} />
        }
      />

      <FAB
        style={styles.fab}
        icon={() => <MaterialIcons name="add" size={24} color={Colors.surface} />}
        color={Colors.surface}
        onPress={() => setAddModalVisible(true)}
        accessibilityLabel="Add event"
      />

      <UpdateEventModal
        visible={updateModalVisible}
        event={selectedEvent}
        onDismiss={() => { setUpdateModalVisible(false); setSelectedEvent(null); }}
        onUpdate={handleUpdateEventSubmit}
        onUpdateSeries={handleUpdateSeriesSubmit}
      />
      <AddEventModal
        visible={addModalVisible}
        onDismiss={() => setAddModalVisible(false)}
        onAdd={handleAddEvent}
        defaultCalendarDayKey={selectedDate}
      />
    </View>
  );
}

// Small helper for icon buttons in event cards
function TouchableIconBtn({ icon, color, onPress }: { icon: string; color: string; onPress: () => void }) {
  return (
    <View
      style={{
        width: 32,
        height: 32,
        borderRadius: 8,
        backgroundColor: color === Colors.error ? "#FEF2F2" : Colors.primaryLight,
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <IconButton
        icon={() => <MaterialIcons name={icon as any} size={16} color={color} />}
        onPress={onPress}
        size={16}
        style={{ margin: 0, padding: 0 }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: Colors.background,
  },
  calendarWrapper: {
    backgroundColor: Colors.surface,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
    ...Shadow.sm,
  },
  arrowBtn: {
    width: 32,
    height: 32,
    borderRadius: Radius.sm,
    backgroundColor: Colors.primaryLight,
    alignItems: "center",
    justifyContent: "center",
  },
  listHeader: {
    paddingHorizontal: 20,
    paddingTop: 16,
    paddingBottom: 8,
    gap: 4,
  },
  listHeaderDate: {
    fontSize: 17,
    fontWeight: "700",
    color: Colors.textPrimary,
  },
  listHeaderText: {
    fontSize: 13,
    fontWeight: "600",
    color: Colors.textTertiary,
    textTransform: "uppercase",
    letterSpacing: 0.8,
  },
  list: {
    flex: 1,
  },
  listContent: {
    paddingHorizontal: 16,
    paddingBottom: 100,
    gap: 10,
  },
  // Event card
  eventCard: {
    backgroundColor: Colors.surface,
    borderRadius: Radius.lg,
    borderWidth: 1,
    borderColor: Colors.border,
    flexDirection: "row",
    overflow: "hidden",
    ...Shadow.sm,
  },
  eventAccent: {
    width: 4,
    backgroundColor: Colors.primary,
  },
  eventBody: {
    flex: 1,
    padding: 14,
  },
  eventTop: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
  },
  eventMeta: {
    flex: 1,
    marginRight: 8,
  },
  titleRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    marginBottom: 4,
  },
  eventTitle: {
    fontSize: 16,
    fontWeight: "600",
    color: Colors.textPrimary,
    flexShrink: 1,
  },
  categoryBadge: {
    borderRadius: Radius.full,
    paddingHorizontal: 8,
    paddingVertical: 2,
  },
  categoryBadgeText: {
    fontSize: 10,
    fontWeight: "600",
    textTransform: "capitalize",
  },
  recurrenceBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 3,
    backgroundColor: Colors.primaryLight,
    borderRadius: Radius.full,
    paddingHorizontal: 7,
    paddingVertical: 2,
  },
  recurrenceBadgeText: {
    fontSize: 10,
    fontWeight: "600",
    color: Colors.primary,
    textTransform: "capitalize",
  },
  timeRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
  },
  eventTime: {
    fontSize: 13,
    color: Colors.primary,
    fontWeight: "500",
  },
  eventActions: {
    flexDirection: "row",
    gap: 6,
  },
  eventDetails: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 6,
    marginTop: 10,
  },
  detailChip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    backgroundColor: Colors.borderLight,
    borderRadius: Radius.full,
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
  detailChipText: {
    fontSize: 12,
    color: Colors.textSecondary,
  },
  eventDescription: {
    fontSize: 13,
    color: Colors.textSecondary,
    marginTop: 8,
    lineHeight: 18,
  },
  // Empty state
  emptyState: {
    alignItems: "center",
    paddingTop: 48,
    gap: 8,
  },
  emptyIconBox: {
    width: 56,
    height: 56,
    borderRadius: Radius.xl,
    backgroundColor: Colors.primaryLight,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 4,
  },
  emptyTitle: {
    fontSize: 16,
    fontWeight: "600",
    color: Colors.textSecondary,
  },
  emptySubtitle: {
    fontSize: 13,
    color: Colors.textTertiary,
  },
  fab: {
    position: "absolute",
    right: 16,
    bottom: 24,
    backgroundColor: Colors.primary,
    borderRadius: Radius.full,
  },
});
