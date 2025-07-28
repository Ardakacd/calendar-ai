import React, { useState, useEffect } from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
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
import { showErrorToast, showSuccessToast } from '../common/toast/toast-message';
interface UpdateEventModalProps {
  visible: boolean;
  event: Event | null;
  onDismiss: () => void;
  onUpdate: (eventId: string, updatedEvent: Partial<Event>) => Promise<void>;
}

export default function UpdateEventModal({
  visible,
  event,
  onDismiss,
  onUpdate,
}: UpdateEventModalProps) {
  const [title, setTitle] = useState('');
  const [location, setLocation] = useState('');
  const [duration, setDuration] = useState('');
  const [datetime, setDatetime] = useState(new Date());
  const [showDatePicker, setShowDatePicker] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    console.log(event);
    if (event) {
      setTitle(event.title);
      setLocation(event.location || '');
      setDuration(event.duration ? event.duration.toString() : '');
      setDatetime(new Date(event.startDate));
    }
  }, [event]);

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
      showSuccessToast('Etkinlik başarıyla güncellendi');
    } catch (error : any) {
      showErrorToast(error.response?.data?.detail || 'Etkinlik güncellenemedi');
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

  return (
    <Portal>
      <Modal
        visible={visible}
        onDismiss={onDismiss}
        contentContainerStyle={styles.modalContainer}
      >
        <Card style={styles.card}>
          <Card.Content>
            <Title style={styles.title}>Etkinlik Düzenle</Title>
            
            <ScrollView >
              <View style={styles.inputContainer}>
                <Text style={styles.label}>Baslik *</Text>
                <TextInput
                  mode="outlined"
                  value={title}
                  onChangeText={setTitle}
                  placeholder="Etkinlik basligi giriniz"
                  style={styles.input}
                />
              </View>

              <View style={styles.inputContainer}>
                <Text style={styles.label}>Tarih & Saat *</Text>
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
                    locale="tr-TR"
                    onChange={onDateChange}
                  />
                )}
              </View>

              <View style={styles.inputContainer}>
                <View style={styles.labelContainer}>
                  <MaterialIcons name="schedule" size={20} color="#6200ee" />
                  <Text style={styles.label}>Süre</Text>
                </View>
                <NumericInput
                  mode="outlined"
                  value={duration}
                  onValueChange={setDuration}
                  placeholder="Etkinlik suresini giriniz (opsiyonel)"
                  style={styles.input}
                />
                <Text style={styles.helperText}>
                  Süreyi dakika cinsinden giriniz (örn: 30 dakika)
                </Text>
              </View>

              <View style={styles.inputContainer}>
                <View style={styles.labelContainer}>
                  <MaterialIcons name="location-on" size={20} color="#6200ee" />
                  <Text style={styles.label}>Konum</Text>
                </View>
                <TextInput
                  mode="outlined"
                  value={location}
                  onChangeText={setLocation}
                  placeholder="Etkinlik konumunu girin (opsiyonel)"
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
                onPress={handleUpdate}
                style={[styles.button, styles.updateButton]}
                loading={loading}
                disabled={loading}
              >
                Update Event
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
  updateButton: {
    backgroundColor: '#6200ee',
  },
}); 