import React, { useState, useEffect } from 'react';
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
import { Event } from '../models/event';
import { showErrorToast } from '../common/toast/toast-message';
interface UpdateAgentEventModalProps {
  visible: boolean;
  event: Event | null;
  updateArguments?: any;
  onDismiss: () => void;
  onUpdate: (eventId: string, updatedEvent: Partial<Event>) => Promise<void>;
}

export default function UpdateAgentEventModal({
  visible,
  event,
  updateArguments = {},
  onDismiss,
  onUpdate,
}: UpdateAgentEventModalProps) {
  const [title, setTitle] = useState('');
  const [location, setLocation] = useState('');
  const [duration, setDuration] = useState('');
  const [datetime, setDatetime] = useState(new Date());
  const [showDatePicker, setShowDatePicker] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (event) {
      console.log(updateArguments);
      console.log(event);
      setTitle(updateArguments.title || event.title);
      setLocation(updateArguments.location || event.location || '');
      setDuration(updateArguments.duration ? updateArguments.duration.toString() : (event.duration ? event.duration.toString() : ''));
      
      // Use update arguments startDate if available, otherwise use current event startDate
      const startDate = updateArguments.startDate ? new Date(updateArguments.startDate) : new Date(event.startDate);
      setDatetime(startDate);
    }
  }, [event, updateArguments]);

  const handleUpdate = async () => {
    if (!event) return;

    const trimmedTitle = title.trim();

    if (!trimmedTitle) {
      showErrorToast('Başlık gereklidir');
      return;
    }

    if (trimmedTitle.length > 255) {
      showErrorToast('Başlık 255 karakterden uzun olamaz');
      return;
    }

    // Duration is optional, but if provided, it must be valid
    let durationMinutes: number | undefined;
    if (duration) {
      try {
        durationMinutes = parseInt(duration);
        if (durationMinutes <= 0) {
          showErrorToast('Süre 0\'dan büyük olmalıdır');
          return;
        }   
      } catch (error) {
        showErrorToast('Geçersiz süre formatı');
        return;
      }
    }

    try {
      setLoading(true);
      await onUpdate(event.id, {
        title: trimmedTitle,
        location: location.trim() || undefined,
        duration: durationMinutes,
        startDate: datetime.toISOString(),
      });
      onDismiss();
    } catch (error) {
      console.error('Error updating event:', error);
    } finally {
      setLoading(false);
    }
  };

  const onDateChange = (event: any, selectedDate?: Date) => {
    if (selectedDate) {
      setDatetime(selectedDate);
    }
  };

  const formatDateTime = (date: Date) => {
    return date.toLocaleString('tr-TR', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    });
  };

  const renderFieldWithPreviousValue = (
    label: string,
    currentValue: string,
    updateValue: string | undefined,
    icon: string,
    inputComponent: React.ReactNode
  ) => (
    <View style={styles.inputContainer}>
      <View style={styles.labelContainer}>
        <MaterialIcons name={icon as any} size={20} color="#6200ee" />
        <Text style={styles.label}>{label}</Text>
      </View>
      
      {inputComponent}
      
      {updateValue && updateValue !== currentValue && (
        <View style={styles.previousValueContainer}>
          <Text style={styles.previousValueLabel}>Önceki değer:</Text>
          <Text style={styles.previousValueText}>{currentValue}</Text>
        </View>
      )}
    </View>
  );

  return (
    <Portal>
      <Modal
        visible={visible}
        onDismiss={onDismiss}
        contentContainerStyle={styles.modalContainer}
      >
        <Card style={styles.card}>
          <Card.Content>
            <Title style={styles.title}>Etkinlik Güncelle</Title>
            
            <ScrollView>
              {renderFieldWithPreviousValue(
                'Başlık *',
                event?.title || '',
                updateArguments.title,
                'edit',
                <TextInput
                  mode="outlined"
                  value={title}
                  onChangeText={setTitle}
                  placeholder="Etkinlik başlığını girin"
                  style={styles.input}
                />
              )}

              {renderFieldWithPreviousValue(
                'Tarih & Saat *',
                event ? formatDateTime(new Date(event.startDate)) : '',
                updateArguments.startDate ? formatDateTime(new Date(updateArguments.startDate)) : undefined,
                'event',
                <Button
                  mode="outlined"
                  onPress={() => setShowDatePicker(true)}
                  style={styles.dateButton}
                  icon="calendar-clock"
                >
                  {formatDateTime(datetime)}
                </Button>
              )}

              {showDatePicker && (
                <DateTimePicker
                  value={datetime}
                  mode="datetime"
                  display="default"
                  locale="tr-TR"
                  onChange={onDateChange}
                />
              )}

              {renderFieldWithPreviousValue(
                'Süre (dakika)',
                event?.duration ? `${event.duration} dakika` : 'Süre belirtilmemiş',
                updateArguments.duration ? `${updateArguments.duration} dakika` : undefined,
                'schedule',
                <NumericInput
                  mode="outlined"
                  value={duration}
                  onValueChange={setDuration}
                  placeholder="Dakika cinsinden süre giriniz"
                  style={styles.input}
                />
              )}

              {renderFieldWithPreviousValue(
                'Konum',
                event?.location || 'Konum belirtilmemiş',
                updateArguments.location,
                'location-on',
                <TextInput
                  mode="outlined"
                  value={location}
                  onChangeText={setLocation}
                  placeholder="Etkinlik konumunu girin (opsiyonel)"
                  style={styles.input}
                />
              )}
            </ScrollView>

            <View style={styles.buttonContainer}>
              <Button
                mode="outlined"
                onPress={onDismiss}
                style={[styles.button, styles.cancelButton]}
                disabled={loading}
              >
                İptal Et
              </Button>
              <Button
                mode="contained"
                onPress={handleUpdate}
                style={[styles.button, styles.updateButton]}
                loading={loading}
                disabled={loading}
              >
                Etkinlik Güncelle
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
    alignItems: 'center',
    padding: 20,
    backgroundColor: 'transparent',
  },
  card: {
    width: '100%',
    maxWidth: 400,
    borderRadius: 16,
    elevation: 8,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 4,
    },
    shadowOpacity: 0.25,
    shadowRadius: 8,
    backgroundColor: '#ffffff',
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
  previousValueContainer: {
    marginTop: 6,
    padding: 8,
    backgroundColor: '#f0f0f0',
    borderRadius: 6,
  },
  previousValueLabel: {
    fontSize: 12,
    color: '#666',
    fontWeight: '500',
    marginBottom: 2,
  },
  previousValueText: {
    fontSize: 12,
    color: '#999',
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
  updateButton: {
    backgroundColor: '#6200ee',
  },
}); 