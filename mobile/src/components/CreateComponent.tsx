import React, { useState } from 'react';
import {
  View,
  StyleSheet,
} from 'react-native';
import {
  Card,
  Text,
  Button,
  IconButton,
} from 'react-native-paper';
import { MaterialIcons } from '@expo/vector-icons';
import AddEventModal from './AddEventModal';
import { EventCreate, Event } from '../models/event';
import { formatDuration, formatLocation } from '../common/formatting';

interface CreateComponentProps {
  eventData: EventCreate[];
  onCreate: (eventData: EventCreate[]) => Promise<void>;
  onCompleted: () => void;
  conflictEvents?: Event[]; 
}

export default function CreateComponent({ eventData, onCreate, onCompleted, conflictEvents }: CreateComponentProps) {
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [isCompleted, setIsCompleted] = useState(false);
  const [currentEventData, setCurrentEventData] = useState<EventCreate[]>(eventData);
  
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('tr-TR', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    });
  };

  const formatConflictEventDate = (dateString: string, duration?: number) => {
    const startDate = new Date(dateString);
    const endDate = duration ? new Date(startDate.getTime() + duration * 60000) : startDate;
    
    const startFormatted = startDate.toLocaleDateString('tr-TR', {
      weekday: 'short',
      month: 'short', 
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    });
    
    if (duration && duration > 0) {
      const endFormatted = endDate.toLocaleTimeString('tr-TR', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
      });
      return `${startFormatted} - ${endFormatted}`;
    }
    
    return startFormatted;
  };

  const handleEdit = (index: number) => {
    setEditingIndex(index);
    setShowEditModal(true);
  };

  const handleDelete = (index: number) => {
    const updatedEvents = currentEventData.filter((_, i) => i !== index);
    setCurrentEventData(updatedEvents);
  };

  const handleCreate = async () => {
    setIsCreating(true);
    try {
      await onCreate(currentEventData);
      setIsCompleted(true); 
      onCompleted();
    } catch (error) {
      console.error('Error creating events:', error);
    } finally {
      setIsCreating(false);
    }
  };

  const handleCancel = () => {
    setIsCompleted(true); 
    onCompleted();
  };

  const handleModalDismiss = () => {
    setShowEditModal(false);
    setEditingIndex(null);
  };

  const handleModalAdd = async (event: Omit<any, 'id' | 'endDate'>) => {
    // This shouldn't be called in edit mode, but keeping for compatibility
    const updatedEventData: EventCreate = {
      title: event.title,
      startDate: event.startDate,
      duration: event.duration,
      location: event.location,
    };
    
    setCurrentEventData([...currentEventData, updatedEventData]);
    setShowEditModal(false);
    setEditingIndex(null);
  };

  const handleModalEdit = async (event: EventCreate) => {
    if (editingIndex !== null) {
      const updatedEvents = [...currentEventData];
      updatedEvents[editingIndex] = event;
      setCurrentEventData(updatedEvents);
    }
    setShowEditModal(false);
    setEditingIndex(null);
  };

  if (isCompleted) {
    return (
      <View style={styles.container}>
        {currentEventData.map((event, index) => (
          <Card key={index} style={[styles.eventCard, styles.disabledCard, index > 0 && styles.cardSpacing]}>
            <Card.Content>
              <View style={styles.eventHeader}>
                <View style={styles.titleContainer}>
                  <Text style={[styles.eventTitle, styles.disabledText]} numberOfLines={2}>
                    {event.title}
                  </Text>
                </View>
              </View>

              <View style={styles.eventDetails}>
                <View style={styles.detailRow}>
                  <MaterialIcons name="schedule" size={16} color="rgba(255, 255, 255, 0.3)" />
                  <Text style={[styles.detailText, styles.disabledText]}>
                    {formatDate(event.startDate)}
                  </Text>
                </View>

                <View style={styles.detailRow}>
                  <MaterialIcons name="timer" size={16} color="rgba(255, 255, 255, 0.3)" />
                  <Text style={[styles.detailText, styles.disabledText]}>
                    {formatDuration(event.duration)}
                  </Text>
                </View>

                <View style={styles.detailRow}>
                  <MaterialIcons name="location-on" size={16} color="rgba(255, 255, 255, 0.3)" />
                  <Text style={[styles.detailText, styles.disabledText]} numberOfLines={1}>
                    {formatLocation(event.location)}
                  </Text>
                </View>
              </View>
            </Card.Content>
          </Card>
        ))}

        <View style={styles.actionButtons}>
          <Button
            mode="outlined"
            disabled={true}
            style={[styles.cancelButton, styles.disabledButton]}
            labelStyle={[styles.cancelButtonText, styles.disabledText]}
            icon="close"
          >
            Iptal
          </Button>
          <Button
            mode="contained"
            disabled={true}
            style={[styles.createButton, styles.disabledButton]}
            labelStyle={[styles.createButtonText, styles.disabledText]}
            icon="check"
          >
            Olustur ({currentEventData.length})
          </Button>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container}>
        
      {conflictEvents && conflictEvents.length > 0 && (
        <Card style={styles.conflictCard}>
          <Card.Content>
            <View style={styles.conflictHeader}>
              <MaterialIcons name="warning" size={20} color="#ff4444" />
              <Text style={styles.conflictWarning}>
                {conflictEvents.length === 1 
                  ? "Bu etkinlik ile çakışma var" 
                  : `${conflictEvents.length} etkinlik ile çakışma var`
                }
              </Text>
            </View>
            {conflictEvents.map((conflictEvent, index) => (
              <View key={conflictEvent.id || index} style={[styles.conflictDetails, index > 0 && styles.conflictDetailsSpacing]}>
                <Text style={styles.conflictEventTitle}>{conflictEvent.title}</Text>
                <Text style={styles.conflictEventTime}>
                  {formatConflictEventDate(conflictEvent.startDate, conflictEvent.duration)}
                </Text>
                {conflictEvent.location && (
                  <Text style={styles.conflictEventLocation}>{conflictEvent.location}</Text>
                )}
              </View>
            ))}
          </Card.Content>
        </Card>
      )}

      {currentEventData.map((event, index) => (
        <Card key={index} style={[styles.eventCard, index > 0 && styles.cardSpacing]}>
          <Card.Content>
            <View style={styles.eventHeader}>
              <View style={styles.titleContainer}>
                <Text style={styles.eventTitle} numberOfLines={2}>
                  {event.title}
                </Text>
              </View>
              <View style={styles.actionButtonsHeader}>
                <IconButton
                  icon="pencil"
                  size={18}
                  onPress={() => handleEdit(index)}
                  style={styles.editButton}
                  iconColor="#667eea"
                />
                {currentEventData.length > 1 && (
                  <IconButton
                    icon="delete"
                    size={18}
                    onPress={() => handleDelete(index)}
                    style={styles.deleteButton}
                    iconColor="#ff4444"
                  />
                )}
              </View>
            </View>

            <View style={styles.eventDetails}>
              <View style={styles.detailRow}>
                <MaterialIcons name="schedule" size={16} color="rgba(255, 255, 255, 0.7)" />
                <Text style={styles.detailText}>
                  {formatDate(event.startDate)}
                </Text>
              </View>

              <View style={styles.detailRow}>
                <MaterialIcons name="timer" size={16} color="rgba(255, 255, 255, 0.7)" />
                <Text style={styles.detailText}>
                  {formatDuration(event.duration)}
                </Text>
              </View>

              <View style={styles.detailRow}>
                <MaterialIcons name="location-on" size={16} color="rgba(255, 255, 255, 0.7)" />
                <Text style={styles.detailText} numberOfLines={1}>
                    {formatLocation(event.location)}
                </Text>
              </View>
            </View>
          </Card.Content>
        </Card>
      ))}

      <View style={styles.actionButtons}>
        <Button
          mode="outlined"
          onPress={handleCancel}
          disabled={isCreating}
          style={styles.cancelButton}
          labelStyle={styles.cancelButtonText}
          icon="close"
        >
          Iptal
        </Button>
        <Button
          mode="contained"
          onPress={handleCreate}
          loading={isCreating}
          disabled={isCreating || currentEventData.length === 0}
          style={styles.createButton}
          labelStyle={styles.createButtonText}
          icon="plus"
        >
          Olustur ({currentEventData.length})
        </Button>
      </View>

      <AddEventModal
        visible={showEditModal}
        onDismiss={handleModalDismiss}
        onAdd={handleModalAdd}
        onEdit={handleModalEdit}
        initialEvent={editingIndex !== null ? {
          title: currentEventData[editingIndex].title,
          startDate: currentEventData[editingIndex].startDate,
          duration: currentEventData[editingIndex].duration,
          location: currentEventData[editingIndex].location,
        } : undefined}
        mode="edit"
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginTop: 12,
  },
  eventCard: {
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.1)',
    marginBottom: 16,
  },
  cardSpacing: {
    marginTop: 8,
  },
  disabledCard: {
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    borderColor: 'rgba(255, 255, 255, 0.05)',
  },
  eventHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  titleContainer: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginRight: 8,
  },
  eventTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: 'white',
    flex: 1,
    lineHeight: 20,
  },
  disabledText: {
    color: 'rgba(255, 255, 255, 0.3)',
  },
  actionButtonsHeader: {
    flexDirection: 'row',
  },
  editButton: {
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    margin: 0,
    marginLeft: 4,
  },
  deleteButton: {
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    margin: 0,
    marginLeft: 4,
  },
  eventDetails: {
    gap: 8,
  },
  detailRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  detailText: {
    fontSize: 14,
    color: 'rgba(255, 255, 255, 0.8)',
    marginLeft: 8,
    flex: 1,
  },
  actionButtons: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: 12,
  },
  createButton: {
    flex: 1,
    backgroundColor: '#667eea',
  },
  createButtonText: {
    color: 'white',
  },
  cancelButton: {
    flex: 1,
    borderColor: 'rgba(255, 255, 255, 0.3)',
  },
  cancelButtonText: {
    color: 'rgba(255, 255, 255, 0.8)',
  },
  disabledButton: {
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    borderColor: 'rgba(255, 255, 255, 0.05)',
  },
  conflictCard: {
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.05)',
    marginTop: 16,
    marginBottom: 16,
  },
  conflictHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  conflictWarning: {
    fontSize: 14,
    color: '#ff4444',
    fontWeight: '600',
    marginLeft: 8,
  },
  conflictDetails: {
    marginLeft: 24,
  },
  conflictEventTitle: {
    fontSize: 14,
    color: 'white',
    fontWeight: '600',
    marginBottom: 4,
  },
  conflictEventTime: {
    fontSize: 12,
    color: 'rgba(255, 255, 255, 0.7)',
    marginBottom: 4,
  },
  conflictEventLocation: {
    fontSize: 12,
    color: 'rgba(255, 255, 255, 0.7)',
  },
  conflictDetailsSpacing: {
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255, 255, 255, 0.1)',
  },
}); 