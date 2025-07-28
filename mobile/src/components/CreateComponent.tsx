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
  eventData: EventCreate;
  onCreate: (eventData: EventCreate) => Promise<void>;
  onCompleted: () => void;
  conflictEvent?: Event; // Add conflict event prop
}

export default function CreateComponent({ eventData, onCreate, onCompleted, conflictEvent }: CreateComponentProps) {
  const [showEditModal, setShowEditModal] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [isCompleted, setIsCompleted] = useState(false);
  const [currentEventData, setCurrentEventData] = useState<EventCreate>(eventData);
  
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

  const handleEdit = () => {
    setShowEditModal(true);
  };

  const handleCreate = async () => {
    setIsCreating(true);
    try {
      await onCreate(currentEventData);
      setIsCompleted(true); 
      onCompleted();
    } catch (error) {
      console.error('Error creating event:', error);
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
  };

  const handleModalAdd = async (event: Omit<any, 'id' | 'endDate'>) => {
    // Update the current event data with the edited values
    const updatedEventData: EventCreate = {
      title: event.title,
      startDate: event.startDate,
      duration: event.duration,
      location: event.location,
    };
    
    setCurrentEventData(updatedEventData);
    setShowEditModal(false);
  };

  const handleModalEdit = async (event: EventCreate) => {
    setCurrentEventData(event);
    setShowEditModal(false);
  };

  if (isCompleted) {
    return (
      <View style={styles.container}>
        <Card style={[styles.eventCard, styles.disabledCard]}>
          <Card.Content>
            <View style={styles.eventHeader}>
              <View style={styles.titleContainer}>
                <Text style={[styles.eventTitle, styles.disabledText]} numberOfLines={2}>
                  {currentEventData.title}
                </Text>
              </View>
            </View>

            <View style={styles.eventDetails}>
              <View style={styles.detailRow}>
                <MaterialIcons name="schedule" size={16} color="rgba(255, 255, 255, 0.3)" />
                <Text style={[styles.detailText, styles.disabledText]}>
                  {formatDate(currentEventData.startDate)}
                </Text>
              </View>

              <View style={styles.detailRow}>
                <MaterialIcons name="timer" size={16} color="rgba(255, 255, 255, 0.3)" />
                <Text style={[styles.detailText, styles.disabledText]}>
                  {formatDuration(currentEventData.duration)}
                </Text>
              </View>

              
                <View style={styles.detailRow}>
                  <MaterialIcons name="location-on" size={16} color="rgba(255, 255, 255, 0.3)" />
                  <Text style={[styles.detailText, styles.disabledText]} numberOfLines={1}>
                    {formatLocation(currentEventData.location)}
                  </Text>
                </View>
              
            </View>
          </Card.Content>
        </Card>

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
            Olustur
          </Button>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container}>
        
      {conflictEvent && (
        <Card style={styles.conflictCard}>
          <Card.Content>
            <View style={styles.conflictHeader}>
              <MaterialIcons name="warning" size={20} color="#ff4444" />
              <Text style={styles.conflictWarning}>Bu etkinlik ile çakışma var</Text>
            </View>
            <View style={styles.conflictDetails}>
              <Text style={styles.conflictEventTitle}>{conflictEvent.title}</Text>
              <Text style={styles.conflictEventTime}>
                {formatConflictEventDate(conflictEvent.startDate, conflictEvent.duration)}
              </Text>
              {conflictEvent.location && (
                <Text style={styles.conflictEventLocation}>{conflictEvent.location}</Text>
              )}
            </View>
          </Card.Content>
        </Card>
      )}
      <Card style={styles.eventCard}>
        <Card.Content>
          <View style={styles.eventHeader}>
            <View style={styles.titleContainer}>
              <Text style={styles.eventTitle} numberOfLines={2}>
                {currentEventData.title}
              </Text>
            </View>
            <IconButton
              icon="pencil"
              size={20}
              onPress={handleEdit}
              style={styles.editButton}
              iconColor="#667eea"
            />
          </View>

          <View style={styles.eventDetails}>
            <View style={styles.detailRow}>
              <MaterialIcons name="schedule" size={16} color="rgba(255, 255, 255, 0.7)" />
              <Text style={styles.detailText}>
                {formatDate(currentEventData.startDate)}
              </Text>
            </View>

            <View style={styles.detailRow}>
              <MaterialIcons name="timer" size={16} color="rgba(255, 255, 255, 0.7)" />
              <Text style={styles.detailText}>
                {formatDuration(currentEventData.duration)}
              </Text>
            </View>

            <View style={styles.detailRow}>
              <MaterialIcons name="location-on" size={16} color="rgba(255, 255, 255, 0.7)" />
              <Text style={styles.detailText} numberOfLines={1}>
                  {formatLocation(currentEventData.location)}
              </Text>
            </View>
          </View>
        </Card.Content>
      </Card>

      

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
          disabled={isCreating}
          style={styles.createButton}
          labelStyle={styles.createButtonText}
          icon="plus"
        >
          Olustur
        </Button>
      </View>

      <AddEventModal
        visible={showEditModal}
        onDismiss={handleModalDismiss}
        onAdd={handleModalAdd}
        onEdit={handleModalEdit}
        initialEvent={{
          title: currentEventData.title,
          startDate: currentEventData.startDate,
          duration: currentEventData.duration,
          location: currentEventData.location,
        }}
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
  editButton: {
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    margin: 0,
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
}); 