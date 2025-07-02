import React, { useState } from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  Alert,
} from 'react-native';
import {
  Modal,
  Portal,
  Text,
  TextInput,
  Button,
  Card,
  Title,
} from 'react-native-paper';
import DateTimePicker from '@react-native-community/datetimepicker';
import { MaterialIcons } from '@expo/vector-icons';
import NumericInput from './NumericInput';

interface Event {
  id: string;
  title: string;
  datetime: string;
  duration?: number;
  location?: string;
}

interface AddEventModalProps {
  visible: boolean;
  onDismiss: () => void;
  onAdd: (event: Omit<Event, 'id'>) => Promise<void>;
}

export default function AddEventModal({
  visible,
  onDismiss,
  onAdd,
}: AddEventModalProps) {
  const [title, setTitle] = useState('');
  const [location, setLocation] = useState('');
  const [duration, setDuration] = useState('');
  const [datetime, setDatetime] = useState(new Date());
  const [showDatePicker, setShowDatePicker] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleAdd = async () => {
    if (!title.trim()) {
      Alert.alert('Error', 'Title is required');
      return;
    }

    // Duration is optional, but if provided, it must be valid
    let durationMinutes: number | undefined;
    if (duration) {
      durationMinutes = parseInt(duration);
      if (durationMinutes <= 0) {
        Alert.alert('Error', 'Duration must be a positive number in minutes');
        return;
      }
    }

    try {
      setLoading(true);
      await onAdd({
        title: title.trim(),
        location: location.trim() || undefined,
        duration: durationMinutes,
        datetime: datetime.toISOString(),
      });
      
      // Reset form
      setTitle('');
      setLocation('');
      setDuration('');
      setDatetime(new Date());
      
      onDismiss();
      Alert.alert('Success', 'Event added successfully');
    } catch (error) {
      console.error('Error adding event:', error);
      Alert.alert('Error', 'Failed to add event');
    } finally {
      setLoading(false);
    }
  };

  const onDateChange = (event: any, selectedDate?: Date) => {
    setShowDatePicker(false);
    if (selectedDate) {
      setDatetime(selectedDate);
    }
  };

  const formatDateTime = (date: Date) => {
    return date.toLocaleString();
  };

  return (
    <Portal>
      <Modal
        visible={visible}
        onDismiss={onDismiss}
        contentContainerStyle={styles.modalContainer}
      >
        <Card>
          <Card.Content>
            <Title style={styles.title}>Add New Event</Title>
            
            <ScrollView>
              <View style={styles.inputContainer}>
                <Text style={styles.label}>Title *</Text>
                <TextInput
                  mode="outlined"
                  value={title}
                  onChangeText={setTitle}
                  placeholder="Enter event title"
                  style={styles.input}
                />
              </View>

              <View style={styles.inputContainer}>
                <Text style={styles.label}>Date & Time *</Text>
                <Button
                  mode="outlined"
                  onPress={() => setShowDatePicker(true)}
                  style={styles.dateButton}
                  icon="calendar-clock"
                >
                  {formatDateTime(datetime)}
                </Button>
                {showDatePicker && (
                  <DateTimePicker
                    value={datetime}
                    mode="datetime"
                    display="default"
                    onChange={onDateChange}
                  />
                )}
              </View>

              <View style={styles.inputContainer}>
                <View style={styles.labelContainer}>
                  <MaterialIcons name="schedule" size={20} color="#6200ee" />
                  <Text style={styles.label}>Duration (minutes)</Text>
                </View>
                <NumericInput
                  mode="outlined"
                  value={duration}
                  onValueChange={setDuration}
                  placeholder="Enter duration in minutes"
                  style={styles.input}
                />
                <Text style={styles.helperText}>
                  Enter the duration in minutes (e.g., 30 for 30 minutes) - Optional
                </Text>
              </View>

              <View style={styles.inputContainer}>
                <View style={styles.labelContainer}>
                  <MaterialIcons name="location-on" size={20} color="#6200ee" />
                  <Text style={styles.label}>Location</Text>
                </View>
                <TextInput
                  mode="outlined"
                  value={location}
                  onChangeText={setLocation}
                  placeholder="Enter event location (optional)"
                  style={styles.input}
                />
              </View>
            </ScrollView>

            <View style={styles.buttonContainer}>
              <Button
                mode="outlined"
                onPress={onDismiss}
                style={[styles.button, styles.cancelButton]}
                disabled={loading}
              >
                Cancel
              </Button>
              <Button
                mode="contained"
                onPress={handleAdd}
                style={[styles.button, styles.addButton]}
                loading={loading}
                disabled={loading}
              >
                Add Event
              </Button>
            </View>
          </Card.Content>
        </Card>
      </Modal>
    </Portal>
  );
}

const styles = StyleSheet.create({
  modalContainer: {
    flex: 1,
    justifyContent: 'center',
    padding: 20,
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
  },
  title: {
    textAlign: 'center',
    marginBottom: 20,
    color: '#1a1a1a',
    fontSize: 22,
    fontWeight: 'bold',
  },
  inputContainer: {
    marginBottom: 16,
  },
  labelContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  label: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginLeft: 8,
  },
  input: {
    backgroundColor: '#f8f9fa',
    borderRadius: 12,
  },
  dateButton: {
    marginTop: 4,
    borderRadius: 12,
    borderColor: '#6200ee',
    borderWidth: 1.5,
  },
  helperText: {
    fontSize: 12,
    color: '#666',
    marginTop: 4,
    fontStyle: 'italic',
  },
  buttonContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 20,
    gap: 12,
  },
  button: {
    flex: 1,
    borderRadius: 12,
    elevation: 2,
  },
  cancelButton: {
    borderColor: '#6200ee',
    borderWidth: 1.5,
  },
  addButton: {
    backgroundColor: '#6200ee',
  },
}); 