import React, { useState, useEffect } from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  Alert,
} from 'react-native';
import { Text, Card, FAB, ActivityIndicator, IconButton } from 'react-native-paper';
import { Calendar, DateData } from 'react-native-calendars';
import { MaterialIcons } from '@expo/vector-icons';
import * as Localization from 'expo-localization';
import { useCalendarAPI } from '../services/api';
import UpdateEventModal from '../components/UpdateEventModal';
import AddEventModal from '../components/AddEventModal';
import { Event, EventCreate } from '../models/event';
import { formatDuration, formatLocation } from '../common/formatting';
import { showErrorToast, showSuccessToast } from '../common/toast/toast-message';

interface MarkedDates {
  [date: string]: {
    marked: boolean;
    dotColor?: string;
    textColor?: string;
    backgroundColor?: string;
    selected?: boolean;
    selectedColor?: string;
    selectedTextColor?: string;
  };
}

export default function CalendarScreen() {
  const [events, setEvents] = useState<Event[]>([]);
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [markedDates, setMarkedDates] = useState<MarkedDates>({});
  const [loading, setLoading] = useState(true);
  const [updateModalVisible, setUpdateModalVisible] = useState(false);
  const [selectedEvent, setSelectedEvent] = useState<Event | null>(null);
  const [addModalVisible, setAddModalVisible] = useState(false);
  const { getEvents, updateEvent, deleteEvent, addEvent } = useCalendarAPI();

  console.log(events);

  useEffect(() => {
    loadEvents();
  }, []);

  useEffect(() => {
    updateMarkedDates(events, selectedDate);
  }, [events, selectedDate]);

  const loadEvents = async () => {
    try {
      setLoading(true);
      const fetchedEvents = await getEvents();
      setEvents(fetchedEvents);
    } catch (error) {
      showErrorToast('Etkinlikler yüklenemedi');
    } finally {
      setLoading(false);
    }
  };

  const updateMarkedDates = (eventList: Event[], selectedDateToUse: string) => {
    const marked: MarkedDates = {};
    
    // First, mark all dates with events
    eventList.forEach(event => {
      const dateKey = event.startDate.split('T')[0];
      if (marked[dateKey]) {
        marked[dateKey].marked = true;
      } else {
        marked[dateKey] = {
          marked: true,
          dotColor: '#6200ee',
        };
      }
    });

    // Always highlight the selected date, regardless of whether it has events
    if (marked[selectedDateToUse]) {
      marked[selectedDateToUse].selected = true;
      marked[selectedDateToUse].selectedColor = '#6200ee';
      marked[selectedDateToUse].selectedTextColor = '#ffffff';
    } else {
      marked[selectedDateToUse] = {
        selected: true,
        selectedColor: '#6200ee',
        selectedTextColor: '#ffffff',
        marked: false,
      };
    }

    setMarkedDates(marked);
  };

  const onDayPress = (day: DateData) => {
    const dateString = day.dateString;
    setSelectedDate(dateString);
  };

  const getEventsForDate = (date: string) => {
    const filteredEvents = events.filter(event => {
      return event.startDate.split('T')[0] === date
    });
    
    // Sort events by startDate in ascending order
    const sortedEvents = filteredEvents.sort((a, b) => {
      return new Date(a.startDate).getTime() - new Date(b.startDate).getTime();
    });
    
    return sortedEvents;
  };
  const formatTime = (datetime: string) => {
    try {
      const date = new Date(datetime);
      if (isNaN(date.getTime())) {
        return 'Invalid time';
      }
      return date.toLocaleTimeString(Localization.locale || 'en-US', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: true
      });
    } catch (error) {
      console.error('Error formatting time:', error, datetime);
      return 'Invalid time';
    }
  };

  const handleUpdateEvent = (event: Event) => {
    setSelectedEvent(event);
    setUpdateModalVisible(true);
  };

  const handleUpdateEventSubmit = async (eventId: string, updatedEvent: Partial<Event>) => {
    try {
      const response = await updateEvent(eventId, updatedEvent);

      if (response) {
        // Update the events list with the updated event
        setEvents(prevEvents => 
          prevEvents.map(event => 
            event.id === eventId ? response : event
          )
        );
        
      }
      

    } catch (error) {
      console.error('Error updating event:', error);
      throw error;
    }
  };

  const handleDeleteEvent = (eventId: string) => {
    Alert.alert(
      'Etkinliği Sil',
      'Bu etkinliği silmek istediğinizden emin misiniz?',
      [
        {
          text: 'İptal',
          style: 'cancel',
        },
        {
          text: 'Sil',
          style: 'destructive',
          onPress: async () => {
            try {
              await deleteEvent(eventId);
              
              // Remove from local state
              const updatedEvents = events.filter(event => event.id !== eventId);
              setEvents(updatedEvents);
              
              showSuccessToast('Etkinlik başarıyla silindi');
            } catch (error) {
              console.error('Error deleting event:', error);
              showErrorToast('Etkinlik silinemedi');
            }
          },
        },
      ]
    );
  };

  const handleAddEvent = async (newEvent: EventCreate) => {
    try {
      const addedEvent = await addEvent(newEvent);
      
      const updatedEvents = [...events, addedEvent];
      setEvents(updatedEvents);
    } catch (error) {
      console.error('Error adding event:', error);
      throw error;
    }
  };

  const selectedDateEvents = getEventsForDate(selectedDate);

  return (
    <View style={styles.container}>
      <Calendar
        onDayPress={onDayPress}
        markedDates={markedDates}
        theme={{
          todayTextColor: '#6200ee',
          dayTextColor: '#2d4150',
          textDisabledColor: '#d9e1e8',
          dotColor: '#6200ee',
          selectedDotColor: '#ffffff',
          arrowColor: '#6200ee',
          monthTextColor: '#2d4150',
          indicatorColor: '#6200ee',
          textDayFontWeight: '300',
          textMonthFontWeight: 'bold',
          textDayHeaderFontWeight: '300',
          textDayFontSize: 16,
          textMonthFontSize: 16,
          textDayHeaderFontSize: 13,
        }}
      />

      <ScrollView style={styles.eventsContainer}>
        <View style={styles.dateHeader}>
          <Text style={styles.dateText}>
            {new Date(selectedDate).toLocaleDateString(Localization.locale || 'en-US', {
              weekday: 'long',
              year: 'numeric',
              month: 'long',
              day: 'numeric',
            })}
          </Text>
          <Text style={styles.eventCount}>
            {selectedDateEvents.length} event{selectedDateEvents.length !== 1 ? 's' : ''}
          </Text>
        </View>

        {loading ? (
          <ActivityIndicator animating={loading} color="#6200ee" style={styles.loadingIndicator} />
        ) : selectedDateEvents.length === 0 ? (
          <Card style={styles.emptyCard}>
            <Card.Content style={styles.emptyCardContent}>
              <MaterialIcons name="event-busy" size={48} color="#ccc" style={styles.emptyIcon} />
              <Text style={styles.emptyText}>No events scheduled for this date</Text>
              <Text style={styles.emptySubtext}>Tap the + button to add an event</Text>
            </Card.Content>
          </Card>
        ) : (
          <>
            {selectedDateEvents.map(event => (
              <Card key={event.id} style={styles.eventCard}>
                <Card.Content>
                  <View style={styles.eventHeader}>
                    <Text style={styles.eventTitle}>{event.title}</Text>
                    <View style={styles.eventTimeContainer}>
                      <MaterialIcons name="access-time" size={16} color="#6200ee" />
                      <Text style={styles.eventTime}>{formatTime(event.startDate)}</Text>
                    </View>
                  </View>
                 
                   
                  <View style={styles.eventBottomContainer}>
                    <View style={styles.eventDetailsContainer}>
                    
                      <View style={styles.eventDetailRow}>
                        <MaterialIcons name="timer" size={16} color="#666" />
                        <Text style={styles.eventDetailText}>{formatDuration(event.duration)}</Text>
                      </View>

                      
                      <View style={styles.eventDetailRow}>
                        <MaterialIcons name="location-on" size={16} color="#666" />
                        <Text style={styles.eventDetailText}>{formatLocation(event.location)}</Text>
                      </View>
                    
                    
                    </View>
                  
                  <View style={styles.eventActions}>
                    <IconButton
                      icon={() => <MaterialIcons name="edit" size={20} color="#6200ee" />}
                      onPress={() => handleUpdateEvent(event)}
                      style={styles.actionButton}
                    />
                    <IconButton
                      icon={() => <MaterialIcons name="delete" size={20} color="#ff4444" />}
                      onPress={() => handleDeleteEvent(event.id)}
                      style={styles.actionButton}
                    />
                  </View>
                  </View>
                </Card.Content>
              </Card>
            ))}
            <View style={styles.bottomSpacer} />
          </>
        )}
      </ScrollView>

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
    backgroundColor: '#f5f5f5',
  },
  eventsContainer: {
    flex: 1,
    padding: 16,
    backgroundColor: '#f5f5f5',
  },
  dateHeader: {
    marginBottom: 16,
  },
  dateText: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 4,
  },
  eventCount: {
    fontSize: 14,
    color: '#666',
  },
  emptyCard: {
    backgroundColor: '#fff',
    marginBottom: 16,
  },
  emptyCardContent: {
    alignItems: 'center',
  },
  emptyIcon: {
    marginBottom: 16,
  },
  emptyText: {
    textAlign: 'center',
    color: '#666',
    fontSize: 16,
    fontStyle: 'italic',
  },
  emptySubtext: {
    color: '#999',
    fontSize: 14,
  },
  eventCard: {
    backgroundColor: '#fff',
    marginBottom: 12,
    elevation: 3,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    borderRadius: 8,
  },
  eventHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 8,
  },
  eventTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
    flex: 1,
    marginRight: 12,
  },
  eventTimeContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#f0f0ff',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
  },
  eventTime: {
    fontSize: 14,
    color: '#6200ee',
    fontWeight: '500',
    marginLeft: 4,
  },
  eventDetailRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 6,
  },
  eventDetailText: {
    fontSize: 13,
    color: '#666',
    marginLeft: 8,
    flex: 1,
  },
  fab: {
    position: 'absolute',
    margin: 16,
    right: 0,
    bottom: 0,
    backgroundColor: '#6200ee',
  },
  bottomSpacer: {
    height: 32,
  },
  eventActions: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    alignItems: 'center',
  },
  eventBottomContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 8,
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: '#f0f0f0',
  },
  eventDetailsContainer: {
    flex: 1,
  },
  loadingIndicator: {
    marginTop: 16,
    marginBottom: 16,
  },
  actionButton: {
    marginLeft: -8,
  },
}); 